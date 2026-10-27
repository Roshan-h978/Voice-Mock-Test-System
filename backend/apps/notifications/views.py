"""
Notification endpoints.

/pending-reviews/, /pending-reviews/mark-alerted/ and /weekly-summary/ are called by n8n
with the X-Automation-Key header. /test-email/ is for signed-in admins.
"""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.attempts import services
from apps.common.permissions import HasAutomationKey
from apps.common.utils import frontend_url

from . import email_service

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
