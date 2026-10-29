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


# ---------------------------------------------------------------------------
# In-app notifications (the bell)
# ---------------------------------------------------------------------------
@override_settings(EVALUATION_DEMO_MODE=True, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend", EMAIL_DELIVERY="django")
class InAppNotificationTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha Adhikari", role="admin")
        self.student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati Sharma")
        self.other = User.objects.create_user("bikash@example.com", "Speak-Clearly-2026", full_name="Bikash Thapa")
        self.test = MockTest.objects.create(title="Everyday conversation")
        Question.objects.create(test=self.test, text="Describe your favourite place.")

    def notifications(self, user):
        self.client.force_authenticate(user)
        return self.client.get(reverse("notifications")).data["results"]

    def test_publishing_a_test_tells_every_student_once(self):
        self.client.force_authenticate(self.admin)
        url = reverse("admin-tests-detail", args=[self.test.pk])
        self.assertEqual(self.client.patch(url, {"status": "published"}, format="json").status_code, 200)
        rows = self.notifications(self.student)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["kind"], "test_published")
        self.assertEqual(rows[0]["link"], f"/student/tests/{self.test.pk}")
        self.assertEqual(len(self.notifications(self.other)), 1)
        self.assertEqual(self.notifications(self.admin), [])
        # Archive and publish again: no second notification.
        self.client.force_authenticate(self.admin)
        self.client.patch(url, {"status": "archived"}, format="json")
        self.client.patch(url, {"status": "published"}, format="json")
        self.assertEqual(len(self.notifications(self.student)), 1)

    def test_review_tells_the_student_and_flag_tells_admins(self):
        attempt = Attempt.objects.create(student=self.student, test=self.test, status=Attempt.Status.NEEDS_REVIEW, overall=50)
        from apps.notifications import inbox

        inbox.review_needed(attempt)
        admin_rows = self.notifications(self.admin)
        self.assertEqual(admin_rows[0]["title"], "Aarati Sharma's test needs a review")
        self.assertEqual(admin_rows[0]["link"], f"/admin/reviews/{attempt.pk}")

        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("admin-attempt-review", args=[attempt.pk]), {"fluency": 70, "notify_student": False}, format="json")
        self.assertEqual(response.status_code, 200)
        rows = self.notifications(self.student)
        self.assertEqual(rows[0]["kind"], "review_published")
        self.assertIn("Everyday conversation", rows[0]["title"])
        self.assertEqual(self.notifications(self.other), [])

    def test_unread_count_mark_read_and_read_all(self):
        from apps.notifications.models import Notification

        first = Notification.objects.create(user=self.student, kind="test_published", title="One")
        Notification.objects.create(user=self.student, kind="test_published", title="Two")
        Notification.objects.create(user=self.other, kind="test_published", title="Not yours")
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(reverse("notifications-unread-count")).data["count"], 2)
        self.assertTrue(self.client.post(reverse("notifications-read", args=[first.pk])).data["is_read"])
        self.assertEqual(self.client.get(reverse("notifications-unread-count")).data["count"], 1)
        self.assertEqual(len(self.client.get(reverse("notifications"), {"unread": 1}).data["results"]), 1)
        self.assertEqual(self.client.post(reverse("notifications-read-all")).data["updated"], 1)
        self.assertEqual(self.client.get(reverse("notifications-unread-count")).data["count"], 0)
        other = Notification.objects.get(user=self.other)
        self.assertEqual(self.client.post(reverse("notifications-read", args=[other.pk])).status_code, 404)

    def test_deleting_the_result_removes_its_notifications(self):
        from apps.notifications.models import Notification

        attempt = Attempt.objects.create(student=self.student, test=self.test, status=Attempt.Status.REVIEWED, overall=70)
        Notification.objects.create(user=self.student, kind="review_published", title="Reviewed", attempt=attempt)
        self.client.force_authenticate(self.admin)
        self.client.delete(reverse("admin-attempt-detail", args=[attempt.pk]))
        self.assertFalse(Notification.objects.filter(user=self.student).exists())

    def test_needs_sign_in(self):
        self.assertEqual(self.client.get(reverse("notifications")).status_code, 401)
