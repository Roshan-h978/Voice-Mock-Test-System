"""Tests for Quick practice, the Mistakes notebook and My progress."""

import shutil
import tempfile
from datetime import timedelta
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.attempts.models import Answer, Attempt
from apps.evaluation import question_writer
from apps.tests_manager.models import MockTest, Question

from . import services
from .models import NotebookMark, PracticeAnswer

TEST_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEST_MEDIA, ignore_errors=True)


def recording():
    return SimpleUploadedFile("answer.webm", b"fake-audio-bytes", content_type="audio/webm")


@override_settings(MEDIA_ROOT=TEST_MEDIA, EVALUATION_DEMO_MODE=True)
class LearningTestCase(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati Sharma", level="intermediate")
        self.admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha Adhikari", role="admin")
        self.client.force_authenticate(self.student)

    def finished_attempt(self, title="Everyday conversation", overall=70, days_ago=0, corrections=None, tip="Add an example."):
        test, _ = MockTest.objects.get_or_create(title=title)
        question = Question.objects.create(test=test, text=f"Question about {title}?")
        when = timezone.now() - timedelta(days=days_ago)
        attempt = Attempt.objects.create(
            student=self.student, test=test, status=Attempt.Status.SCORED, overall=overall,
            fluency=overall, pronunciation=overall, grammar=overall, submitted_at=when,
        )
        Answer.objects.create(
            attempt=attempt, question=question, question_order=1, question_text=question.text, audio="x.webm",
            duration_seconds=60, corrections=corrections or [], tip=tip,
        )
        return attempt


class PracticeTests(LearningTestCase):
    def test_topics(self):
        topics = self.client.get(reverse("practice-topics")).data
        self.assertIn({"value": "travel", "label": "Travel and places"}, topics)

    def test_ai_question_for_a_topic(self):
        data = self.client.post(reverse("practice-question"), {"source": "ai", "topic": "food"}, format="json").data
        food = {text for topic, _level, text, _hint in question_writer.DEMO_BANK if topic == "food"}
        self.assertIn(data["question_text"], food)
        self.assertEqual((data["topic"], data["topic_label"], data["time_limit"]), ("food", "Food and cooking", 60))

    def test_question_from_the_tests(self):
        response = self.client.post(reverse("practice-question"), {"source": "tests"}, format="json")
        self.assertEqual(response.status_code, 404)  # nothing published yet
        test = MockTest.objects.create(title="Job interview", answer_seconds=90)
        Question.objects.create(test=test, text="Tell me about yourself.", hint="Studies, interests")
        test.status = MockTest.Status.PUBLISHED
        test.save()
        data = self.client.post(reverse("practice-question"), {"source": "tests"}, format="json").data
        self.assertEqual((data["question_text"], data["time_limit"], data["topic_label"]), ("Tell me about yourself.", 90, "Job interview"))

    def test_answer_is_scored_saved_listed_and_deleted(self):
        body = {"audio": recording(), "question_text": "Describe a meal you remember well.", "topic": "food", "source": "ai", "time_limit": 60, "duration_seconds": 41.5}
        response = self.client.post(reverse("practice-answers"), body, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertTrue(data["is_demo"])
        self.assertTrue(0 < data["overall"] <= 100)
        self.assertEqual(data["duration_seconds"], 41.5)
        self.assertEqual(data["topic_label"], "Food and cooking")
        self.assertTrue(data["audio_url"].startswith("http://testserver/media/recordings/practice/"))
        self.assertEqual(self.client.get(reverse("practice-answers")).data["count"], 1)

        answer = PracticeAnswer.objects.get()
        storage, name = answer.audio.storage, answer.audio.name
        self.assertTrue(storage.exists(name))
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.client.delete(reverse("practice-answer-detail", args=[answer.pk])).status_code, 204)
        self.assertFalse(storage.exists(name))

    def test_off_topic_practice_answer_is_limited(self):
        weak = {**question_writer.feedback.demo_analysis(), "answers_question": "no", "relevance": 10}
        with mock.patch("apps.evaluation.feedback.demo_analysis", return_value=weak):
            data = self.client.post(
                reverse("practice-answers"), {"audio": recording(), "question_text": "Describe a meal you remember well."}, format="multipart"
            ).data
        self.assertLessEqual(data["overall"], 25)
        self.assertIn("didn't answer the question", data["score_notes"][0])

    def test_other_students_and_admins_cannot_see_it(self):
        self.client.post(reverse("practice-answers"), {"audio": recording(), "question_text": "Describe a meal you remember well."}, format="multipart")
        answer = PracticeAnswer.objects.get()
        other = User.objects.create_user("bikash@example.com", "Speak-Clearly-2026", full_name="Bikash Thapa")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(reverse("practice-answer-detail", args=[answer.pk])).status_code, 404)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(reverse("practice-answers")).status_code, 403)

    def test_missing_question_is_refused(self):
        response = self.client.post(reverse("practice-answers"), {"audio": recording(), "question_text": " "}, format="multipart")
        self.assertEqual(response.status_code, 400)


class NotebookTests(LearningTestCase):
    def test_corrections_are_grouped_and_can_be_marked_learned(self):
        same = {"said": "I goes to school", "better": "I go to school"}
        self.finished_attempt(corrections=[same, {"said": "He don't like", "better": "He doesn't like"}], days_ago=2)
        self.finished_attempt(title="Daily life", corrections=[{"said": "i goes to school!", "better": "I go to school."}], tip="Add an example.")
        PracticeAnswer.objects.create(student=self.student, question_text="Practice question?", audio="p.webm", corrections=[same], tip="Slow down a little.")
        # An unfinished test doesn't count.
        unfinished = Attempt.objects.create(student=self.student, test=MockTest.objects.first())
        Answer.objects.create(attempt=unfinished, question_order=2, question_text="Q", audio="u.webm", corrections=[{"said": "secret", "better": "hidden"}])

        data = self.client.get(reverse("notebook")).data
        self.assertEqual(data["totals"], {"corrections": 2, "tips": 2, "learned": 0})
        top = data["corrections"][0]
        self.assertEqual((top["said"], top["count"]), ("I goes to school", 3))
        self.assertEqual({source["kind"] for source in top["sources"]}, {"test", "practice"})
        self.assertEqual(data["tips"][0]["text"], "Add an example.")
        self.assertEqual(data["tips"][0]["count"], 2)

        response = self.client.post(reverse("notebook-learned"), {"key": top["key"], "learned": True}, format="json")
        self.assertEqual(response.status_code, 200)
        data = self.client.get(reverse("notebook")).data
        self.assertEqual(len(data["corrections"]), 1)
        self.assertEqual(data["totals"]["learned"], 1)
        learned = self.client.get(reverse("notebook"), {"show": "learned"}).data
        self.assertEqual([row["said"] for row in learned["corrections"]], ["I goes to school"])
        self.client.post(reverse("notebook-learned"), {"key": top["key"], "learned": False}, format="json")
        self.assertFalse(NotebookMark.objects.exists())

    def test_bad_key_is_refused(self):
        self.assertEqual(self.client.post(reverse("notebook-learned"), {"key": "nope", "learned": True}, format="json").status_code, 400)

    def test_empty_notebook(self):
        self.assertEqual(self.client.get(reverse("notebook")).data, {"corrections": [], "tips": [], "totals": {"corrections": 0, "tips": 0, "learned": 0}})


class ProgressTests(LearningTestCase):
    def test_progress_numbers(self):
        for days_ago, score in ((40, 50), (9, 55), (8, 60), (3, 65), (2, 70), (1, 75)):
            self.finished_attempt(title=f"Test {days_ago % 2}", overall=score, days_ago=days_ago)
        PracticeAnswer.objects.create(student=self.student, question_text="P?", audio="p.webm", overall=80, fluency=82, pronunciation=78, grammar=60, duration_seconds=30)

        data = self.client.get(reverse("progress"), {"days": 30}).data
        self.assertEqual(len(data["timeline"]), 5)  # the 40-day-old test is outside the range
        self.assertEqual(len(data["practice"]), 1)
        self.assertEqual(data["totals"]["tests_completed"], 6)
        self.assertEqual(data["totals"]["practice_answers"], 1)
        self.assertEqual(data["totals"]["minutes_spoken"], 7)  # 6 x 60 s + 30 s
        self.assertEqual(data["skills"]["overall"]["current"], 70)  # 60, 65, 70, 75, 80
        self.assertEqual(data["skills"]["overall"]["change"], 18)  # previous: 50, 55
        self.assertEqual(data["focus_skill"], "grammar")
        self.assertTrue(data["focus_advice"])
        self.assertEqual({row["title"] for row in data["best_by_test"]}, {"Test 0", "Test 1"})
        self.assertEqual(len(data["activity"]), 84)
        self.assertEqual(data["streak"], {"current": 4, "longest": 4})  # today (practice), 1, 2, 3 days ago

        all_time = self.client.get(reverse("progress"), {"days": 0}).data
        self.assertEqual(len(all_time["timeline"]), 6)

    def test_streak_rules(self):
        today = timezone.localdate()
        days = {today - timedelta(days=offset) for offset in (1, 2, 5, 6, 7)}
        self.assertEqual(services._streaks(days, today), (2, 3))
        self.assertEqual(services._streaks(set(), today), (0, 0))

    def test_new_student_gets_empty_progress(self):
        data = self.client.get(reverse("progress")).data
        self.assertEqual(data["timeline"], [])
        self.assertIsNone(data["focus_skill"])
        self.assertEqual(data["streak"], {"current": 0, "longest": 0})

    def test_admins_use_their_own_pages(self):
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(reverse("progress")).status_code, 403)
