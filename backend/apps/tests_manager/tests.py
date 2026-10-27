"""Tests for mock tests, questions and the seed_demo command."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.attempts.models import Attempt

from .models import MockTest, Question


def make_admin():
    return User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha Adhikari", role="admin")


def make_student(email="aarati@example.com"):
    return User.objects.create_user(email, "Speak-Clearly-2026", full_name="Aarati Sharma")


def make_test(status=MockTest.Status.PUBLISHED, questions=2, **extra):
    test = MockTest.objects.create(title=extra.pop("title", "Everyday conversation"), status=MockTest.Status.DRAFT, **extra)
    for number in range(1, questions + 1):
        Question.objects.create(test=test, text=f"Question number {number}: tell me about your day.")
    test.status = status
    test.save()
    return test


class AdminTestManagementTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_authenticate(self.admin)

    def test_create_add_questions_and_publish(self):
        created = self.client.post(
            reverse("admin-tests-list"),
            {"title": "Travel and places", "level": "intermediate", "answer_seconds": 45},
            format="json",
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(created.data["status"], "draft")
        self.assertEqual(created.data["created_by_name"], "Nisha Adhikari")
        test_url = reverse("admin-tests-detail", args=[created.data["id"]])

        too_early = self.client.patch(test_url, {"status": "published"}, format="json")
        self.assertEqual(too_early.status_code, status.HTTP_400_BAD_REQUEST)

        for text in ("Describe a trip you enjoyed.", "Where would you like to travel next, and why?"):
            response = self.client.post(reverse("admin-questions-list"), {"test": created.data["id"], "text": text}, format="json")
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        orders = list(Question.objects.filter(test_id=created.data["id"]).values_list("order", flat=True))
        self.assertEqual(orders, [1, 2])

        published = self.client.patch(test_url, {"status": "published"}, format="json")
        self.assertEqual(published.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(published.data["published_at"])
        self.assertEqual(published.data["question_count"], 2)

    def test_reorder_and_delete_questions(self):
        test = make_test(status=MockTest.Status.DRAFT, questions=3)
        first, second, third = test.questions.all()
        response = self.client.post(
            reverse("admin-questions-reorder"), {"test": test.id, "order": [third.id, first.id, second.id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [third.id, first.id, second.id])

        self.client.delete(reverse("admin-questions-detail", args=[third.id]))
        self.assertEqual(list(test.questions.values_list("order", flat=True)), [1, 2])

    def test_reorder_needs_every_question(self):
        test = make_test(questions=2)
        response = self.client.post(
            reverse("admin-questions-reorder"), {"test": test.id, "order": [test.questions.first().id]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_published_test_keeps_at_least_one_question(self):
        test = make_test(questions=1)
        response = self.client.delete(reverse("admin-questions-detail", args=[test.questions.first().id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_test_with_attempts_cannot_be_deleted(self):
        test = make_test()
        Attempt.objects.create(student=make_student(), test=test)
        response = self.client.delete(reverse("admin-tests-detail", args=[test.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_question_list_needs_a_test_id(self):
        self.assertEqual(self.client.get(reverse("admin-questions-list")).status_code, status.HTTP_400_BAD_REQUEST)

    def test_students_cannot_manage_tests(self):
        self.client.force_authenticate(make_student())
        self.assertEqual(self.client.get(reverse("admin-tests-list")).status_code, status.HTTP_403_FORBIDDEN)


class StudentTestTests(APITestCase):
    def setUp(self):
        self.student = make_student()
        self.client.force_authenticate(self.student)
        self.published = make_test(title="Everyday conversation", questions=3)
        make_test(title="Draft test", status=MockTest.Status.DRAFT)

    def test_students_see_only_published_tests(self):
        response = self.client.get(reverse("test-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["title"] for row in response.data], ["Everyday conversation"])
        self.assertEqual(response.data[0]["question_count"], 3)
        self.assertEqual(response.data[0]["estimated_minutes"], 4)  # 3 x (15 + 60) seconds

    def test_detail_has_questions_and_start_state(self):
        response = self.client.get(reverse("test-detail", args=[self.published.id]))
        self.assertEqual(len(response.data["questions"]), 3)
        self.assertTrue(response.data["can_start"])
        self.assertIsNone(response.data["in_progress_attempt_id"])

    def test_drafts_are_hidden_from_students(self):
        draft = MockTest.objects.get(title="Draft test")
        self.assertEqual(self.client.get(reverse("test-detail", args=[draft.id])).status_code, status.HTTP_404_NOT_FOUND)


class SeedDemoCommandTests(TestCase):
    @override_settings(DEBUG=True)
    def test_seed_adds_tests_and_demo_student_once(self):
        admin = make_admin()
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())  # running twice changes nothing
        self.assertEqual(MockTest.objects.published().count(), 3)
        self.assertEqual(Question.objects.count(), 13)
        self.assertEqual(MockTest.objects.first().created_by, admin)
        self.assertTrue(User.objects.get(email="student@example.com").check_password("student123"))

    @override_settings(DEBUG=False)
    def test_no_demo_accounts_outside_development(self):
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(MockTest.objects.count(), 3)
        self.assertFalse(User.objects.exists())
