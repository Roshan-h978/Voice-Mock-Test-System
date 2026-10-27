"""Tests for speech measurements, scoring rules and the OpenAI / Anthropic calls (mocked)."""

import io
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User

from . import feedback, scoring
from .speech_to_text import (
    EvaluationError,
    EvaluationNotConfigured,
    NoSpeechDetected,
    Segment,
    Transcript,
    demo_transcript,
    transcribe,
)

LIVE_KEYS = {"EVALUATION_DEMO_MODE": False, "OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "test-key"}


def fake_response(status_code=200, payload=None, text=""):
    response = mock.Mock()
    response.status_code = status_code
    response.ok = 200 <= status_code < 300
    response.json.return_value = payload or {}
    response.text = text
    return response


def claude_payload(text):
    return {"content": [{"type": "text", "text": text}]}


class MeasurementTests(SimpleTestCase):
    def test_demo_transcript_measurements(self):
        metrics = scoring.measure_delivery(demo_transcript())
        self.assertEqual(metrics.filler_count, 1)
        self.assertEqual(metrics.long_pauses, 1)
        self.assertTrue(100 <= metrics.words_per_minute <= 160)
        self.assertGreater(metrics.clarity, 80)
        self.assertGreater(metrics.fluency_auto, 80)

    def test_slow_speech_lowers_fluency(self):
        slow = Transcript(text="I like my home town very much", segments=[Segment(0, 20, "I like my home town very much")])
        self.assertLess(scoring.measure_delivery(slow).fluency_auto, 60)

    def test_no_confidence_values_means_no_clarity(self):
        transcript = Transcript(text="hello there my friend", duration=3)
        self.assertIsNone(scoring.measure_delivery(transcript).clarity)


class ScoringRuleTests(SimpleTestCase):
    def test_overall_uses_the_weights(self):
        self.assertEqual(scoring.overall_score(80, 60, 70, {"fluency": 40, "pronunciation": 30, "grammar": 30}), 71)
        self.assertEqual(scoring.overall_score(80, None, 70, {"fluency": 50, "pronunciation": 0, "grammar": 50}), 75)

    def test_headlines(self):
        self.assertEqual(scoring.headline_for(85), "Great job!")
        self.assertEqual(scoring.headline_for(65), "Good progress")
        self.assertEqual(scoring.headline_for(40), "Keep practising")

    def test_review_reasons(self):
        reasons = scoring.answer_review_reasons(overall=50, word_count=8, clarity=40, relevance=20)
        self.assertEqual(len(reasons), 4)
        self.assertEqual(scoring.answer_review_reasons(overall=90, word_count=80, clarity=90, relevance=90), [])


@override_settings(**LIVE_KEYS)
class SpeechToTextTests(SimpleTestCase):
    def test_parses_segments(self):
        payload = {
            "text": "My favourite place is the park.",
            "duration": 4.2,
            "segments": [{"start": 0.2, "end": 3.9, "text": "My favourite place is the park.", "avg_logprob": -0.2, "no_speech_prob": 0.01}],
        }
        with mock.patch("apps.evaluation.speech_to_text.requests.post", return_value=fake_response(payload=payload)) as post:
            transcript = transcribe(io.BytesIO(b"audio"), filename="answer.webm")
        self.assertEqual(len(transcript.words), 6)
        self.assertEqual(transcript.segments[0].avg_logprob, -0.2)
        self.assertEqual(post.call_args.kwargs["data"]["response_format"], "verbose_json")

    def test_empty_transcript_means_no_speech(self):
        with mock.patch("apps.evaluation.speech_to_text.requests.post", return_value=fake_response(payload={"text": ""})):
            with self.assertRaises(NoSpeechDetected):
                transcribe(io.BytesIO(b"audio"))

    def test_bad_key_is_reported_as_not_configured(self):
        with mock.patch("apps.evaluation.speech_to_text.requests.post", return_value=fake_response(401, text="bad key")):
            with self.assertRaises(EvaluationNotConfigured):
                transcribe(io.BytesIO(b"audio"))

    @override_settings(OPENAI_API_KEY="")
    def test_missing_key_is_reported_as_not_configured(self):
        with self.assertRaises(EvaluationNotConfigured):
            transcribe(io.BytesIO(b"audio"))

    @mock.patch("apps.evaluation.speech_to_text.time.sleep")
    def test_retries_once_then_fails(self, _sleep):
        with mock.patch("apps.evaluation.speech_to_text.requests.post", return_value=fake_response(503)) as post:
            with self.assertRaises(EvaluationError):
                transcribe(io.BytesIO(b"audio"))
        self.assertEqual(post.call_count, 2)


@override_settings(**LIVE_KEYS)
class FeedbackTests(SimpleTestCase):
    def test_reads_json_inside_the_reply_and_clamps_scores(self):
        reply = 'Here you go: {"grammar": 140, "coherence": "70", "relevance": 55, "strengths": ["You were clear."], "tip": "Add an example.", "corrections": [{"said": "I goes", "better": "I go"}, {"bad": 1}]}'
        with mock.patch("apps.evaluation.feedback.requests.post", return_value=fake_response(payload=claude_payload(reply))):
            result = feedback.analyse_answer(question="Q", transcript="I goes home", level="beginner", measurements={})
        self.assertEqual(result["grammar"], 100)
        self.assertEqual(result["coherence"], 70)
        self.assertEqual(result["pronunciation_estimate"], 70)
        self.assertEqual(result["corrections"], [{"said": "I goes", "better": "I go"}])

    @mock.patch("apps.evaluation.feedback.time.sleep")
    def test_summary_falls_back_when_claude_is_unavailable(self, _sleep):
        answer = mock.Mock(question_text="Q", overall=72, strengths=["You spoke clearly."], tip="Slow down.")
        with mock.patch("apps.evaluation.feedback.requests.post", return_value=fake_response(529)):
            summary = feedback.summarise_attempt(test_title="T", level="beginner", skills={"overall": 72}, answers=[answer])
        self.assertEqual(summary["strengths"], ["You spoke clearly."])
        self.assertEqual(summary["tip"], "Slow down.")
        self.assertTrue(summary["summary"])


@override_settings(EVALUATION_DEMO_MODE=True)
class EvaluateAnswerTests(TestCase):
    def test_demo_pipeline_returns_every_field(self):
        result = scoring.evaluate_answer(io.BytesIO(b"audio"), question_text="Describe your favourite place.")
        self.assertTrue(result.is_demo)
        self.assertTrue(0 <= result.overall <= 100)
        self.assertFalse(result.needs_review)
        self.assertIn("needs_review", result.as_model_fields())


class EvaluationConfigViewTests(APITestCase):
    def test_admin_only(self):
        admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha", role="admin")
        student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati")
        self.client.force_authenticate(student)
        self.assertEqual(self.client.get(reverse("evaluation-config")).status_code, 403)
        self.client.force_authenticate(admin)
        response = self.client.get(reverse("evaluation-config"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("sk-", str(response.data))
        self.assertEqual(sum(response.data["weights"].values()), 100)
