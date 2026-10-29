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

    def test_test_with_attempts_needs_with_results_to_be_deleted(self):
        test = make_test()
        Attempt.objects.create(student=make_student(), test=test)
        response = self.client.delete(reverse("admin-tests-detail", args=[test.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Archive it", response.data["detail"])
        self.assertTrue(MockTest.objects.filter(pk=test.id).exists())

    def test_test_deleted_together_with_its_results(self):
        test = make_test()
        other = make_test(title="Job interview")
        student = make_student()
        Attempt.objects.create(student=student, test=test, status=Attempt.Status.SCORED, overall=70)
        kept = Attempt.objects.create(student=student, test=other)
        response = self.client.delete(reverse("admin-tests-detail", args=[test.id]) + "?with_results=true")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MockTest.objects.filter(pk=test.id).exists())
        self.assertFalse(Question.objects.filter(test_id=test.id).exists())
        self.assertEqual(list(Attempt.objects.values_list("pk", flat=True)), [kept.pk])

    def test_question_list_needs_a_test_id(self):
        self.assertEqual(self.client.get(reverse("admin-questions-list")).status_code, status.HTTP_400_BAD_REQUEST)

    def test_students_cannot_manage_tests(self):
        self.client.force_authenticate(make_student())
        self.assertEqual(self.client.get(reverse("admin-tests-list")).status_code, status.HTTP_403_FORBIDDEN)


class ArchivedTestQuestionTests(APITestCase):
    def setUp(self):
        self.client.force_authenticate(make_admin())
        self.test = make_test(status=MockTest.Status.ARCHIVED, questions=2)
        self.first, self.second = self.test.questions.order_by("order")

    def test_questions_of_an_archived_test_cannot_change(self):
        url = reverse("admin-questions-detail", args=[self.first.id])
        edit = self.client.patch(url, {"text": "A completely new question text."}, format="json")
        self.assertEqual(edit.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.delete(url).status_code, status.HTTP_400_BAD_REQUEST)
        reorder = self.client.post(
            reverse("admin-questions-reorder"), {"test": self.test.id, "order": [self.second.id, self.first.id]}, format="json"
        )
        self.assertEqual(reorder.status_code, status.HTTP_400_BAD_REQUEST)
        self.first.refresh_from_db()
        self.assertEqual((self.first.order, self.test.questions.count()), (1, 2))
        self.assertTrue(self.first.text.startswith("Question number 1"))


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


# ---------------------------------------------------------------------------
# AI-written questions (demo bank in tests; the real AI is mocked)
# ---------------------------------------------------------------------------
@override_settings(EVALUATION_DEMO_MODE=True)
class GenerateQuestionsTests(APITestCase):
    def setUp(self):
        self.admin = make_admin()
        self.client.force_authenticate(self.admin)
        self.test = make_test(status=MockTest.Status.DRAFT, questions=0, title="Travel and places")

    def test_suggestions_are_returned_but_not_saved(self):
        response = self.client.post(reverse("admin-questions-generate"), {"test": self.test.id, "count": 4}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["questions"]), 4)
        self.assertTrue(response.data["is_demo"])
        self.assertTrue(all(item["text"] and "hint" in item for item in response.data["questions"]))
        from apps.evaluation.question_writer import DEMO_BANK

        travel = {text for topic, _level, text, _hint in DEMO_BANK if topic == "travel"}
        self.assertTrue({item["text"] for item in response.data["questions"]} <= travel)  # matched to the test's title
        self.assertEqual(self.test.questions.count(), 0)

    def test_existing_questions_are_not_suggested_again(self):
        from apps.evaluation.question_writer import DEMO_BANK

        for _topic, _level, text, _hint in DEMO_BANK[:30]:
            Question.objects.create(test=self.test, text=text)
        response = self.client.post(reverse("admin-questions-generate"), {"test": self.test.id, "count": 10}, format="json")
        existing = set(self.test.questions.values_list("text", flat=True))
        self.assertTrue(response.data["questions"])
        self.assertFalse(existing & {item["text"] for item in response.data["questions"]})

    def test_bulk_add_appends_in_order(self):
        Question.objects.create(test=self.test, text="Already here: describe your town.")
        body = {"test": self.test.id, "questions": [{"text": "  First   new question?  ", "hint": "a hint"}, {"text": "Second new question?", "answer_seconds": 90}]}
        response = self.client.post(reverse("admin-questions-bulk"), body, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual([row["order"] for row in response.data], [1, 2, 3])
        self.assertEqual(response.data[1]["text"], "First new question?")
        self.assertEqual(response.data[2]["time_limit"], 90)

    def test_archived_test_and_bad_input_are_refused(self):
        archived = make_test(status=MockTest.Status.ARCHIVED, title="Old test")
        self.assertEqual(self.client.post(reverse("admin-questions-generate"), {"test": archived.id}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post(reverse("admin-questions-bulk"), {"test": archived.id, "questions": [{"text": "A fine question?"}]}, format="json").status_code,
            400,
        )
        self.assertEqual(self.client.post(reverse("admin-questions-generate"), {"test": self.test.id, "count": 50}, format="json").status_code, 400)
        self.assertEqual(self.client.post(reverse("admin-questions-bulk"), {"test": self.test.id, "questions": [{"text": "Hi"}]}, format="json").status_code, 400)

    def test_students_cannot_generate(self):
        self.client.force_authenticate(make_student())
        self.assertEqual(self.client.post(reverse("admin-questions-generate"), {"test": self.test.id}, format="json").status_code, 403)

    @override_settings(EVALUATION_DEMO_MODE=False, AI_PROVIDER="groq", GROQ_API_KEY="gsk-test")
    def test_real_ai_reply_is_cleaned(self):
        from unittest import mock

        reply = {"questions": [
            {"text": "1. Describe a city you would like to visit.", "hint": "Place, reasons"},
            {"text": "Describe a city you would like to visit.", "hint": "duplicate"},
            {"text": "Too short"},
            "Q3) Talk about the best journey you have ever taken.",
        ]}
        with mock.patch("apps.evaluation.feedback.call_model", return_value=reply) as call:
            response = self.client.post(reverse("admin-questions-generate"), {"test": self.test.id, "count": 3, "topic": "cities"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([q["text"] for q in response.data["questions"]], ["Describe a city you would like to visit.", "Talk about the best journey you have ever taken."])
        self.assertFalse(response.data["is_demo"])
        self.assertIn('"topic": "cities"', call.call_args.args[1])

    @override_settings(EVALUATION_DEMO_MODE=False, AI_PROVIDER="groq", GROQ_API_KEY="", GEMINI_API_KEY="")
    def test_missing_key_gives_a_clear_message(self):
        response = self.client.post(reverse("admin-questions-generate"), {"test": self.test.id}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertIn("GROQ_API_KEY", response.data["detail"])
