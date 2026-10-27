"""Serializers for sign-up, sign-in, profiles, password changes and invitations."""

from django.conf import settings
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import AccountToken

User = get_user_model()


def _clean_name(value: str) -> str:
    value = " ".join(value.split())
    if len(value) < 2:
        raise serializers.ValidationError("Enter a full name.")
    return value


def _check_password(password: str, user) -> None:
    """Run Django's password validators and return their messages as a field error."""
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


# ---------------------------------------------------------------------------
# Signed-in user
# ---------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    """The signed-in user's own account."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "level",
            "phone",
            "uses_default_password",
            "date_joined",
            "last_login",
        )
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("full_name", "phone", "level")

    def validate_full_name(self, value):
        return _clean_name(value)

    def validate_phone(self, value):
        return value.strip()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.has_usable_password():  # accounts created with "Continue with Google"
            raise serializers.ValidationError(
                'Your account signs in with Google, so it has no password yet. Sign out and use "Forgot password?" to set one.'
            )
        if not user.check_password(value):
            raise serializers.ValidationError("Your current password is not correct.")
        return value

    def validate_new_password(self, value):
        _check_password(value, self.context["request"].user)
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "uses_default_password"])
        return user


# ---------------------------------------------------------------------------
# Sign-up and sign-in
# ---------------------------------------------------------------------------
class RegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    invite_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_full_name(self, value):
        return _clean_name(value)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists. Sign in instead.")
        return email

    def validate(self, attrs):
        token = attrs.pop("invite_token", "").strip()
        invitation = None
        if token:
            invitation = AccountToken.find_valid(token, AccountToken.INVITATION_PURPOSES)
            if invitation is None:
                raise serializers.ValidationError(
                    {"invite_token": "This invitation link has expired or was already used."}
                )
            if invitation.email != attrs["email"]:
                raise serializers.ValidationError({"email": "Use the email address the invitation was sent to."})
        elif not settings.ALLOW_PUBLIC_REGISTRATION:
            raise serializers.ValidationError("Sign-up is by invitation only. Ask your teacher for an invitation.")

        candidate = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            _check_password(attrs["password"], candidate)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"password": exc.detail}) from exc

        attrs["invitation"] = invitation
        return attrs

    def create(self, validated_data):
        invitation = validated_data.pop("invitation")
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data["full_name"],
            role=invitation.role if invitation else User.Role.STUDENT,
        )
        if invitation:
            invitation.mark_used()
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """Email + password sign-in that also returns the user's details."""

    default_error_messages = {
        "no_active_account": "The email or password is incorrect, or the account is suspended.",
    }

    def validate(self, attrs):
        attrs[self.username_field] = attrs.get(self.username_field, "").strip().lower()
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        record = AccountToken.find_valid(attrs["token"], [AccountToken.Purpose.PASSWORD_RESET])
        if record is None or record.user is None or not record.user.is_active:
            raise serializers.ValidationError({"token": "This reset link has expired or was already used. Ask for a new one."})
        try:
            _check_password(attrs["new_password"], record.user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({"new_password": exc.detail}) from exc
        attrs["record"] = record
        return attrs


# ---------------------------------------------------------------------------
# Invitations
# ---------------------------------------------------------------------------
class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=User.Role.choices, default=User.Role.STUDENT)

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("This person already has an account.")
        return email

    def validate_full_name(self, value):
        return " ".join(value.split())


class InvitationInfoSerializer(serializers.ModelSerializer):
    """What the Register page shows for an invitation link."""

    role = serializers.CharField(read_only=True)

    class Meta:
        model = AccountToken
        fields = ("email", "name", "role", "expires_at")
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Admin user management
# ---------------------------------------------------------------------------
class AdminUserSerializer(serializers.ModelSerializer):
    attempt_count = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    last_attempt_at = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "level",
            "phone",
            "is_active",
            "date_joined",
            "last_login",
            "attempt_count",
            "average_score",
            "last_attempt_at",
        )
        read_only_fields = ("id", "email", "date_joined", "last_login")

    def get_attempt_count(self, obj):
        return getattr(obj, "attempt_count", None)

    def get_average_score(self, obj):
        value = getattr(obj, "average_score", None)
        return round(value) if value is not None else None

    def get_last_attempt_at(self, obj):
        return getattr(obj, "last_attempt_at", None)

    def validate_full_name(self, value):
        return _clean_name(value)

    def validate(self, attrs):
        current_user = self.context["request"].user
        if self.instance and self.instance.pk == current_user.pk:
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "You can't suspend your own account."})
            if "role" in attrs and attrs["role"] != self.instance.role:
                raise serializers.ValidationError({"role": "You can't change your own role."})
        return attrs

    def update(self, instance, validated_data):
        # A superuser counts as an admin everywhere, so a demoted admin loses the Django-admin flags too.
        if validated_data.get("role") == User.Role.STUDENT:
            validated_data["is_staff"] = False
            validated_data["is_superuser"] = False
        return super().update(instance, validated_data)


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField(max_length=4096)
    invite_token = serializers.CharField(required=False, allow_blank=True)
