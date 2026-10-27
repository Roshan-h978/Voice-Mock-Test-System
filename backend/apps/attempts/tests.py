"""Tests for taking a test, results, admin review, dashboard and reports (demo scoring mode)."""

import csv
import io
import shutil
import tempfile
from unittest import mock

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.evaluation.feedback import demo_analysis
from apps.evaluation.speech_to_text import NoSpeechDetected
from apps.tests_manager.models import MockTest, Question

from .models import Answer, Attempt

TEST_MEDIA = tempfile.mkdtemp()


def tearDownModule():
    shutil.rmtree(TEST_MEDIA, ignore_errors=True)


def recording(name="answer.webm", content_type="audio/webm", content=b"fake-audio-bytes"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def weak_analysis(**_kwargs):
    return {**demo_analysis(), "grammar": 30, "coherence": 30, "relevance": 30}


@override_settings(
    MEDIA_ROOT=TEST_MEDIA,
    EVALUATION_DEMO_MODE=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_DELIVERY="django",
)
class AttemptTestCase(APITestCase):
    def setUp(self):
        self.student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati Sharma")
        self.admin = User.objects.create_user(
            "nisha@example.com", "Speak-Clearly-2026", full_name="Nisha Adhikari", role="admin"
        )
        self.test = MockTest.objects.create(title="Everyday conversation", status=MockTest.Status.DRAFT)
        self.questions = [
            Question.objects.create(test=self.test, text="Describe your favourite place."),
            Question.objects.create(test=self.test, text="Talk about a friend you admire."),
        ]
        self.test.status = MockTest.Status.PUBLISHED
        self.test.save()
        self.client.force_authenticate(self.student)

    def start(self):
        response = self.client.post(reverse("attempt-list"), {"test": self.test.id}, format="json")
        return response.data["id"]

    def answer(self, attempt_id, question, **kwargs):
        return self.client.post(
            reverse("attempt-answer-upload", args=[attempt_id]),
            {"question": question.id, "audio": kwargs.pop("audio", recording()), "duration_seconds": 31.5},
            format="multipart",
        )

    def answer_all(self, attempt_id):
        for question in self.questions:
            self.assertEqual(self.answer(attempt_id, question).status_code, status.HTTP_201_CREATED)


class TakingATestTests(AttemptTestCase):
    def test_start_and_resume(self):
        first = self.client.post(reverse("attempt-list"), {"test": self.test.id}, format="json")
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(first.data["questions"]), 2)
        again = self.client.post(reverse("attempt-list"), {"test": self.test.id}, format="json")
        self.assertEqual(again.status_code, status.HTTP_200_OK)
        self.assertEqual(again.data["id"], first.data["id"])

    def test_answer_is_scored_and_saved(self):
        attempt_id = self.start()
        response = self.answer(attempt_id, self.questions[0])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for field in ("fluency", "pronunciation", "grammar", "overall"):
            self.assertIsInstance(response.data[field], int)
        self.assertTrue(response.data["is_demo"])
        self.assertTrue(response.data["transcript"])
        self.assertTrue(response.data["audio_url"].startswith("http://testserver/media/recordings/"))

    def test_recording_again_replaces_the_answer(self):
        attempt_id = self.start()
        self.answer(attempt_id, self.questions[0])
        self.answer(attempt_id, self.questions[0])
        self.assertEqual(Answer.objects.filter(attempt_id=attempt_id).count(), 1)

    def test_rejects_files_that_are_not_audio(self):
        attempt_id = self.start()
        response = self.answer(attempt_id, self.questions[0], audio=recording("notes.txt", "text/plain"))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported audio type", response.data["detail"])

    def test_silent_recording_asks_to_record_again(self):
        attempt_id = self.start()
        with mock.patch("apps.evaluation.scoring.transcribe", side_effect=NoSpeechDetected()):
            response = self.answer(attempt_id, self.questions[0])
        self.assertEqual(response.status_code, 422)
        self.assertIn("could not hear any speech", response.data["detail"])

    def test_submit_needs_every_answer(self):
        attempt_id = self.start()
        self.answer(attempt_id, self.questions[0])
        response = self.client.post(reverse("attempt-submit", args=[attempt_id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("1 question left", response.data["detail"])

    def test_submit_returns_results(self):
        attempt_id = self.start()
        self.answer_all(attempt_id)
        response = self.client.post(reverse("attempt-submit", args=[attempt_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(response.data["status"], ("scored", "needs_review"))
        self.assertIsInstance(response.data["overall"], int)
        self.assertTrue(response.data["headline"])
        self.assertTrue(response.data["summary"])
        self.assertEqual(len(response.data["strengths"]), 2)
        self.assertEqual(len(response.data["answers"]), 2)
        self.assertTrue(response.data["test"]["allow_retake"])  # the Results page offers "Take this test again"

        stats = self.client.get(reverse("my-stats")).data
        self.assertEqual(stats["completed_tests"], 1)
        self.assertEqual(stats["average_score"], response.data["overall"])

    def test_no_retake_when_the_test_does_not_allow_it(self):
        self.test.allow_retake = False
        self.test.save()
        attempt_id = self.start()
        self.answer_all(attempt_id)
        self.client.post(reverse("attempt-submit", args=[attempt_id]))
        response = self.client.post(reverse("attempt-list"), {"test": self.test.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_students_only_see_their_own_attempts(self):
        attempt_id = self.start()
        other = User.objects.create_user("bikash@example.com", "Speak-Clearly-2026", full_name="Bikash Thapa")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get(reverse("attempt-detail", args=[attempt_id])).status_code, 404)
        self.assertEqual(self.answer(attempt_id, self.questions[0]).status_code, 404)

    def test_missing_things_get_a_plain_message(self):
        attempt_id = self.start()
        self.test.status = MockTest.Status.DRAFT
        self.test.save()
        other = User.objects.create_user("bikash@example.com", "Speak-Clearly-2026", full_name="Bikash Thapa")
        self.client.force_authenticate(other)
        for url in (reverse("attempt-detail", args=[attempt_id]), reverse("test-detail", args=[self.test.id])):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertNotIn("matches the given query", response.data["detail"])
            self.assertIn("couldn't find", response.data["detail"])


class ReviewAndReportTests(AttemptTestCase):
    def finished_weak_attempt(self):
        attempt_id = self.start()
        with mock.patch("apps.evaluation.feedback.demo_analysis", side_effect=weak_analysis):
            self.answer_all(attempt_id)
        self.client.post(reverse("attempt-submit", args=[attempt_id]))
        return Attempt.objects.get(pk=attempt_id)

    def test_weak_attempt_goes_to_the_review_queue(self):
        attempt = self.finished_weak_attempt()
        self.assertEqual(attempt.status, Attempt.Status.NEEDS_REVIEW)
        self.assertTrue(attempt.review_reasons)

        self.client.force_authenticate(self.admin)
        queue = self.client.get(reverse("admin-attempts"), {"status": "needs_review"})
        self.assertEqual(queue.data["count"], 1)
        self.assertEqual(queue.data["results"][0]["student"]["full_name"], "Aarati Sharma")

    def test_admin_review_updates_scores_and_emails_the_student(self):
        attempt = self.finished_weak_attempt()
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            reverse("admin-attempt-review", args=[attempt.id]),
            {"grammar": 70, "tip": "Slow down a little on long words.", "reviewer_note": "Good effort."},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["email_sent"])
        self.assertEqual(response.data["attempt"]["status"], "reviewed")
        self.assertEqual(response.data["attempt"]["grammar"], 70)
        self.assertEqual(response.data["attempt"]["reviewer_name"], "Nisha Adhikari")
        self.assertEqual(mail.outbox[-1].to, ["aarati@example.com"])

    def test_students_cannot_review(self):
        attempt = self.finished_weak_attempt()
        response = self.client.post(reverse("admin-attempt-review", args=[attempt.id]), {"grammar": 90}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_report_and_csv(self):
        self.finished_weak_attempt()
        self.client.force_authenticate(self.admin)

        dashboard = self.client.get(reverse("admin-dashboard")).data
        self.assertEqual(dashboard["attempts"]["this_week"], 1)
        self.assertEqual(dashboard["needs_review"], 1)

        report = self.client.get(reverse("admin-reports")).data
        self.assertEqual(report["totals"]["attempts"], 1)
        self.assertEqual(report["by_test"][0]["title"], "Everyday conversation")

        export = self.client.get(reverse("admin-reports-export"))
        self.assertEqual(export.status_code, status.HTTP_200_OK)
        self.assertEqual(export["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("Aarati Sharma", export.content.decode("utf-8-sig"))

    def test_report_survives_dates_at_the_ends_of_the_calendar(self):
        self.client.force_authenticate(self.admin)
        for params in ({"date_from": "0001-01-01"}, {"date_to": "9999-12-31"}):
            self.assertEqual(self.client.get(reverse("admin-reports"), params).status_code, status.HTTP_200_OK, params)

    def test_csv_does_not_turn_names_into_spreadsheet_formulas(self):
        self.student.full_name = '=HYPERLINK("http://example.com","Open")'
        self.student.save()
        self.finished_weak_attempt()
        self.client.force_authenticate(self.admin)
        rows = list(csv.reader(io.StringIO(self.client.get(reverse("admin-reports-export")).content.decode("utf-8-sig"))))
        self.assertEqual(rows[1][1], "'" + self.student.full_name)
        self.assertEqual(rows[1][9], str(Attempt.objects.get().overall))

    def test_admin_list_shows_unsubmitted_attempts_last(self):
        finished = self.finished_weak_attempt()
        unfinished = Attempt.objects.create(student=self.student, test=self.test)
        self.client.force_authenticate(self.admin)
        rows = self.client.get(reverse("admin-attempts"), {"status": "all"}).data["results"]
        self.assertEqual([row["id"] for row in rows], [finished.id, unfinished.id])

    def test_rescoring_a_missing_recording_explains_the_problem(self):
        attempt = self.finished_weak_attempt()
        answer = attempt.answers.first()
        answer.audio.storage.delete(answer.audio.name)
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("evaluation-rescore-answer", args=[answer.id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("recording for this answer is missing", response.data["detail"])
