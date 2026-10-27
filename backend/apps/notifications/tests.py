"""Tests for email delivery and the n8n automation endpoints."""

from datetime import timedelta
from unittest import mock

import requests
from django.core import mail
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.attempts.models import Attempt
from apps.tests_manager.models import MockTest, Question

from . import email_service

KEY = "test-automation-key"


@override_settings(AUTOMATION_API_KEY=KEY)
class AutomationEndpointTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha Adhikari", role="admin")
        student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati Sharma")
        test = MockTest.objects.create(title="Everyday conversation")
        Question.objects.create(test=test, text="Describe your favourite place.")
        self.flagged = Attempt.objects.create(
            student=student,
            test=test,
            status=Attempt.Status.NEEDS_REVIEW,
            overall=52,
            review_reasons=["Overall score under 65%"],
            submitted_at=timezone.now() - timedelta(hours=1),
        )
        Attempt.objects.create(student=student, test=test, status=Attempt.Status.SCORED, overall=81, submitted_at=timezone.now())

    def get(self, name, key=KEY):
        return self.client.get(reverse(name), HTTP_X_AUTOMATION_KEY=key)

    def test_key_is_required(self):
        self.assertEqual(self.client.get(reverse("notifications-pending-reviews")).status_code, 403)
        self.assertEqual(self.get("notifications-pending-reviews", key="wrong").status_code, 403)

    @override_settings(AUTOMATION_API_KEY="")
    def test_endpoints_are_off_without_a_configured_key(self):
        self.assertEqual(self.get("notifications-pending-reviews", key="").status_code, 403)

    def test_pending_reviews_then_mark_alerted(self):
        response = self.get("notifications-pending-reviews")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["admin_emails"], ["nisha@example.com"])
        self.assertTrue(response.data["attempts"][0]["review_url"].endswith(f"/admin/reviews/{self.flagged.id}"))

        marked = self.client.post(
            reverse("notifications-mark-alerted"), {"ids": [self.flagged.id]}, format="json", HTTP_X_AUTOMATION_KEY=KEY
        )
        self.assertEqual(marked.data["updated"], 1)
        self.assertEqual(self.get("notifications-pending-reviews").data["count"], 0)

    def test_mark_alerted_validates_ids(self):
        response = self.client.post(
            reverse("notifications-mark-alerted"), {"ids": "1,2"}, format="json", HTTP_X_AUTOMATION_KEY=KEY
        )
        self.assertEqual(response.status_code, 400)

    def test_weekly_summary(self):
        response = self.get("notifications-weekly-summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["attempts"], 2)
        self.assertEqual(response.data["needs_review"], 1)
        self.assertEqual(response.data["top_tests"][0]["title"], "Everyday conversation")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_admin_test_email(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("notifications-test-email"), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox[0].to, ["nisha@example.com"])


class EmailServiceTests(SimpleTestCase):
    def test_render_escapes_html(self):
        html, text = email_service.render_email(heading="Hi <b>", paragraphs=["<script>x</script>"])
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("<script>x</script>", text)

    @override_settings(EMAIL_DELIVERY="n8n", N8N_WEBHOOK_BASE_URL="http://n8n.test/webhook", AUTOMATION_API_KEY=KEY)
    def test_n8n_delivery_posts_to_the_webhook(self):
        response = mock.Mock(ok=True, status_code=200)
        with mock.patch("apps.notifications.email_service.requests.post", return_value=response) as post:
            email_service.send_password_reset(
                email="aarati@example.com", name="Aarati", link="http://x/reset", expires_at=timezone.now()
            )
        self.assertEqual(post.call_args.args[0], "http://n8n.test/webhook/vmt/password-reset-email")
        self.assertEqual(post.call_args.kwargs["headers"]["X-Automation-Key"], KEY)
        self.assertEqual(post.call_args.kwargs["json"]["link"], "http://x/reset")

    @override_settings(EMAIL_DELIVERY="n8n", N8N_WEBHOOK_BASE_URL="http://n8n.test/webhook")
    def test_n8n_failure_raises(self):
        with mock.patch("apps.notifications.email_service.requests.post", side_effect=requests.ConnectionError):
            with self.assertRaises(email_service.EmailDeliveryError):
                email_service.send_invitation(
                    email="a@example.com", name="", role="student", link="http://x", invited_by="Nisha", expires_at=timezone.now()
                )
