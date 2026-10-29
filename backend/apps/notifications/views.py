"""
Notification endpoints.

/pending-reviews/, /pending-reviews/mark-alerted/ and /weekly-summary/ are called by n8n
with the X-Automation-Key header. /test-email/ is for signed-in admins.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.attempts import services
from apps.common.permissions import HasAutomationKey
from apps.common.utils import StandardPagination, frontend_url

from . import email_service
from .models import Notification
from .serializers import NotificationSerializer

User = get_user_model()


def admin_emails() -> list[str]:
    return list(User.objects.filter(role=User.Role.ADMIN, is_active=True).values_list("email", flat=True))


class AutomationView(APIView):
    """Base for endpoints n8n calls: no user login, only the shared key."""

    authentication_classes = []
    permission_classes = [HasAutomationKey]
    throttle_classes = []


class PendingReviewsView(AutomationView):
    def get(self, request):
        attempts = services.pending_review_alerts()
        return Response(
            {
                "count": len(attempts),
                "admin_emails": admin_emails(),
                "review_queue_url": frontend_url("/admin/reviews"),
                "attempts": attempts,
            }
        )


class MarkAlertedView(AutomationView):
    def post(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list) or not all(isinstance(item, int) for item in ids):
            return Response({"detail": "Send ids as a list of attempt ids."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"updated": services.mark_alerted(ids)})


class WeeklySummaryView(AutomationView):
    def get(self, request):
        return Response({**services.weekly_summary(), "admin_emails": admin_emails()})


class TestEmailView(APIView):
    """Sends a test email to check the SMTP settings. Body: {"to": "optional@address"}"""

    permission_classes = [IsAdmin]

    def post(self, request):
        to = str(request.data.get("to") or request.user.email).strip()
        try:
            validate_email(to)
        except ValidationError:
            return Response({"detail": "Enter a valid email address."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            email_service.send_test_email(to)
        except email_service.EmailDeliveryError:
            return Response(
                {"detail": "The email could not be sent. Check the email settings in backend/.env."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({"detail": f"Test email sent to {to}."})


# ---------------------------------------------------------------------------
# In-app notifications (the bell): for the signed-in person only
# ---------------------------------------------------------------------------
class MyNotificationListView(generics.ListAPIView):
    """Newest first. ?unread=1 shows only unread ones."""

    serializer_class = NotificationSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread") in ("1", "true"):
            queryset = queryset.filter(read_at__isnull=True)
        return queryset


class UnreadCountView(APIView):
    def get(self, request):
        return Response({"count": Notification.objects.filter(user=request.user, read_at__isnull=True).count()})


class MarkReadView(APIView):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, user=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    def post(self, request):
        updated = Notification.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"updated": updated})
