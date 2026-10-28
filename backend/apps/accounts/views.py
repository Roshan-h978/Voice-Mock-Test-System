"""Authentication, profile and admin user-management endpoints."""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.db import transaction
from django.db.models import Avg, Count, F, Max, Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.attempts.models import FINISHED_STATUSES, Attempt
from apps.attempts.services import delete_attempts
from apps.common.utils import ServiceError, StandardPagination, frontend_url
from apps.notifications import email_service

from . import google_auth
from .models import AccountToken
from .permissions import IsAdmin
from .serializers import (
    AdminUserCreateSerializer,
    AdminUserSerializer,
    ChangePasswordSerializer,
    GoogleLoginSerializer,
    InvitationCreateSerializer,
    InvitationInfoSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SafeTokenRefreshSerializer,
    UserSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def tokens_for(user) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def sign_out_everywhere(user) -> None:
    """Blacklist every refresh token the user holds."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class AuthThrottleMixin:
    """Stricter rate limit for sign-in, sign-up and password-reset requests."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


# ---------------------------------------------------------------------------
# Sign-up, sign-in, sign-out
# ---------------------------------------------------------------------------
class RegisterView(AuthThrottleMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        return Response({"user": UserSerializer(user).data, **tokens_for(user)}, status=status.HTTP_201_CREATED)


class LoginView(AuthThrottleMixin, TokenObtainPairView):
    serializer_class = LoginSerializer


class GoogleConfigView(APIView):
    """Tells the React app whether to show "Continue with Google" and with which client ID."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        enabled = google_auth.is_enabled()
        return Response(
            {
                "enabled": enabled,
                "client_id": settings.GOOGLE_CLIENT_ID if enabled else None,
                "setup_hint": not enabled and settings.DEBUG,
            }
        )


class GoogleLoginView(AuthThrottleMixin, APIView):
    """Body: {"credential": "<Google ID token>", "invite_token": "<optional>"}"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claims = google_auth.verify_credential(serializer.validated_data["credential"])
        with transaction.atomic():
            user, created = google_auth.user_for_claims(claims, serializer.validated_data.get("invite_token", ""))
        update_last_login(None, user)
        return Response(
            {"user": UserSerializer(user).data, "created": created, **tokens_for(user)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class RefreshView(TokenRefreshView):
    """Exchange a refresh token for a new access token (and a new refresh token)."""

    serializer_class = SafeTokenRefreshSerializer


class LogoutView(APIView):
    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass  # already expired or blacklisted
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Own profile
# ---------------------------------------------------------------------------
class MeView(generics.RetrieveUpdateAPIView):
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def patch(self, request, *args, **kwargs):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Your password has been changed."})


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
class PasswordResetRequestView(AuthThrottleMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"], is_active=True).first()
        if user:
            record, raw_token = AccountToken.issue(
                purpose=AccountToken.Purpose.PASSWORD_RESET,
                email=user.email,
                name=user.full_name,
                user=user,
                lifetime=timedelta(hours=settings.PASSWORD_RESET_VALID_HOURS),
            )
            try:
                email_service.send_password_reset(
                    email=user.email,
                    name=user.full_name,
                    link=frontend_url("/reset-password", token=raw_token),
                    expires_at=record.expires_at,
                )
            except email_service.EmailDeliveryError:
                logger.exception("Password reset email failed for user %s", user.pk)
        # Same answer whether or not the account exists, so emails can't be discovered.
        return Response({"detail": "If an account exists for that email, we've sent a link to reset your password."})


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = serializer.validated_data["record"]
        user = record.user
        with transaction.atomic():
            user.set_password(serializer.validated_data["new_password"])
            user.save(update_fields=["password", "uses_default_password"])
            record.mark_used()
            sign_out_everywhere(user)
        return Response({"detail": "Your password has been reset. You can sign in now."})


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------
class InvitationDetailView(APIView):
    """Lets the Register page check an invitation link and prefill the email."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        record = AccountToken.find_valid(token, AccountToken.INVITATION_PURPOSES)
        if record is None:
            return Response(
                {"detail": "This invitation link has expired or was already used."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(InvitationInfoSerializer(record).data)


class AdminInviteView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = InvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        purpose = (
            AccountToken.Purpose.INVITE_ADMIN if data["role"] == User.Role.ADMIN else AccountToken.Purpose.INVITE_STUDENT
        )
        record, raw_token = AccountToken.issue(
            purpose=purpose,
            email=data["email"],
            name=data.get("full_name", ""),
            created_by=request.user,
            lifetime=timedelta(days=settings.INVITE_VALID_DAYS),
        )
        link = frontend_url("/register", invite=raw_token)

        email_sent = True
        try:
            email_service.send_invitation(
                email=record.email,
                name=record.name,
                role=data["role"],
                link=link,
                invited_by=request.user.full_name,
                expires_at=record.expires_at,
            )
        except email_service.EmailDeliveryError:
            logger.exception("Invitation email failed for %s", record.email)
            email_sent = False

        body = {
            "detail": f"Invitation sent to {record.email}." if email_sent else "Invitation saved, but the email could not be sent. Share the link below.",
            "email": record.email,
            "role": data["role"],
            "expires_at": record.expires_at,
            "email_sent": email_sent,
        }
        if not email_sent:
            body["invite_link"] = link
        return Response(body, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Admin user management
# ---------------------------------------------------------------------------
def users_with_stats():
    finished = Q(attempts__status__in=FINISHED_STATUSES)
    return User.objects.annotate(
        attempt_count=Count("attempts", filter=finished),
        average_score=Avg("attempts__overall", filter=finished),
        last_attempt_at=Max("attempts__submitted_at"),
    )


class AdminUserListView(generics.ListCreateAPIView):
    """Students and admins with filters: ?role= ?status=active|suspended ?level= ?search= ?ordering=

    POST adds a person directly: {email, full_name, role, level, phone?, password}.
    """

    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    pagination_class = StandardPagination
    ORDERING = {
        "name": "full_name",
        "-name": "-full_name",
        "joined": "date_joined",
        "-joined": "-date_joined",
        # People without a score go last on every database (PostgreSQL would put them first).
        "score": F("average_score").asc(nulls_last=True),
        "-score": F("average_score").desc(nulls_last=True),
    }

    def get_queryset(self):
        params = self.request.query_params
        queryset = users_with_stats()

        role = params.get("role")
        if role in User.Role.values:
            queryset = queryset.filter(role=role)

        state = params.get("status")
        if state == "active":
            queryset = queryset.filter(is_active=True)
        elif state == "suspended":
            queryset = queryset.filter(is_active=False)

        level = params.get("level")
        if level in User.Level.values:
            queryset = queryset.filter(level=level)

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(Q(full_name__icontains=search) | Q(email__icontains=search))

        return queryset.order_by(self.ORDERING.get(params.get("ordering"), "full_name"), "id")

    def create(self, request, *args, **kwargs):
        serializer = AdminUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        data = AdminUserSerializer(users_with_stats().get(pk=user.pk), context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class AdminUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """View, update or delete a user.

    PATCH: full_name, level, phone, role, is_active (suspend), password (sets a new one and signs them out).
    DELETE: removes the account with all its results and recordings.
    """

    permission_classes = [IsAdmin]
    serializer_class = AdminUserSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return users_with_stats()

    def perform_update(self, serializer):
        new_password = "password" in serializer.validated_data
        user = serializer.save()
        if new_password:
            sign_out_everywhere(user)

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            raise ServiceError("You can't delete your own account.")
        with transaction.atomic():
            delete_attempts(Attempt.objects.filter(student=instance))
            instance.delete()
