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

LIVE_KEYS = {"EVALUATION_DEMO_MODE": False, "AI_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test", "ANTHROPIC_API_KEY": "test-key"}


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



# ---------------------------------------------------------------------------
# Free Groq option (AI_PROVIDER=groq)
# ---------------------------------------------------------------------------
GROQ = {"EVALUATION_DEMO_MODE": False, "AI_PROVIDER": "groq", "GROQ_API_KEY": "gsk-test", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}


def chat_payload(text):
    return {"choices": [{"message": {"role": "assistant", "content": text}}]}


@override_settings(**GROQ)
class GroqTests(SimpleTestCase):
    def test_transcription_uses_groq_whisper(self):
        payload = {"text": "I like to read books in the evening.", "duration": 3.1, "segments": [{"start": 0, "end": 3, "text": "I like to read books in the evening."}]}
        with mock.patch("apps.evaluation.speech_to_text.requests.post", return_value=fake_response(payload=payload)) as post:
            transcript = transcribe(io.BytesIO(b"audio"), filename="answer.webm")
        self.assertEqual(len(transcript.words), 8)
        self.assertEqual(post.call_args.args[0], "https://api.groq.com/openai/v1/audio/transcriptions")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer gsk-test")
        data = post.call_args.kwargs["data"]
        self.assertEqual((data["model"], data["response_format"]), ("whisper-large-v3-turbo", "verbose_json"))
        self.assertNotIn("timestamp_granularities[]", data)

    def test_feedback_uses_groq_chat_in_json_mode(self):
        reply = '{"grammar": 82, "coherence": 75, "relevance": 90, "strengths": ["You answered clearly."], "tip": "Add one example.", "corrections": []}'
        with mock.patch("apps.evaluation.feedback.requests.post", return_value=fake_response(payload=chat_payload(reply))) as post:
            result = feedback.analyse_answer(question="Q", transcript="I like books", level="beginner", measurements={})
        self.assertEqual((result["grammar"], result["tip"]), (82, "Add one example."))
        self.assertEqual(post.call_args.args[0], "https://api.groq.com/openai/v1/chat/completions")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model"], "openai/gpt-oss-120b")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(body["messages"][0]["role"], "system")

    def test_feedback_retries_without_optional_settings_after_a_400(self):
        reply = '{"grammar": 70}'
        responses = [fake_response(400, text="unsupported"), fake_response(payload=chat_payload(reply))]
        with mock.patch("apps.evaluation.feedback.requests.post", side_effect=responses) as post:
            result = feedback.analyse_answer(question="Q", transcript="I like books", level="", measurements={})
        self.assertEqual(result["grammar"], 70)
        second = post.call_args_list[1].kwargs["json"]
        self.assertNotIn("response_format", second)
        self.assertNotIn("reasoning_effort", second)

    def test_rate_limit_is_retried_then_reported_as_busy(self):
        with mock.patch("apps.evaluation.feedback.time.sleep"), mock.patch(
            "apps.evaluation.feedback.requests.post", return_value=fake_response(429)
        ) as post:
            with self.assertRaises(EvaluationError):
                feedback.analyse_answer(question="Q", transcript="I like books", level="", measurements={})
        self.assertEqual(post.call_count, 2)

    @override_settings(GROQ_API_KEY="")
    def test_missing_groq_key_is_reported_as_not_configured(self):
        with self.assertRaises(EvaluationNotConfigured):
            transcribe(io.BytesIO(b"audio"))
        with self.assertRaises(EvaluationNotConfigured):
            feedback.analyse_answer(question="Q", transcript="text here", level="", measurements={})


class GroqConfigViewTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha", role="admin")
        self.client.force_authenticate(admin)

    @override_settings(**GROQ)
    def test_setup_check_reports_groq(self):
        data = self.client.get(reverse("evaluation-config")).data
        self.assertEqual(data["provider"], "groq")
        self.assertTrue(data["speech_to_text_ready"] and data["feedback_ready"])
        self.assertEqual(data["missing_keys"], [])
        self.assertEqual((data["transcribe_model"], data["scoring_model"]), ("whisper-large-v3-turbo", "openai/gpt-oss-120b"))

    @override_settings(**{**GROQ, "GROQ_API_KEY": ""})
    def test_setup_check_names_the_missing_key(self):
        self.assertEqual(self.client.get(reverse("evaluation-config")).data["missing_keys"], ["GROQ_API_KEY"])


# ---------------------------------------------------------------------------
# Free Gemini backup and the "Test AI connection" button
# ---------------------------------------------------------------------------
GEMINI = {"GEMINI_API_KEY": "gem-test", "GEMINI_MODEL": "gemini-3.5-flash-lite"}


@override_settings(**GROQ, **GEMINI)
class GeminiBackupTests(SimpleTestCase):
    def test_busy_groq_hands_over_to_gemini(self):
        reply = chat_payload('{"grammar": 66, "tip": "Speak a little slower."}')
        responses = [fake_response(429), fake_response(429), fake_response(payload=reply)]
        with mock.patch("apps.evaluation.feedback.time.sleep"), mock.patch(
            "apps.evaluation.feedback.requests.post", side_effect=responses
        ) as post:
            result = feedback.analyse_answer(question="Q", transcript="I like books", level="", measurements={})
        self.assertEqual((result["grammar"], result["tip"]), (66, "Speak a little slower."))
        last = post.call_args_list[-1]
        self.assertEqual(last.args[0], "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions")
        self.assertEqual(last.kwargs["headers"]["Authorization"], "Bearer gem-test")
        self.assertEqual(last.kwargs["json"]["model"], "gemini-3.5-flash-lite")

    @override_settings(GROQ_API_KEY="")
    def test_gemini_answers_when_the_groq_key_is_missing(self):
        with mock.patch("apps.evaluation.feedback.requests.post", return_value=fake_response(payload=chat_payload('{"grammar": 90}'))) as post:
            result = feedback.analyse_answer(question="Q", transcript="I like books", level="", measurements={})
        self.assertEqual(result["grammar"], 90)
        self.assertEqual(post.call_count, 1)

    def test_summary_uses_gemini_when_groq_is_down(self):
        answer = mock.Mock(question_text="Q", overall=72, strengths=["You spoke clearly."], tip="Slow down.")
        reply = chat_payload('{"summary": "Good work.", "strengths": ["A", "B"], "tip": "T", "next_step": "N"}')
        with mock.patch("apps.evaluation.feedback.time.sleep"), mock.patch(
            "apps.evaluation.feedback.requests.post", side_effect=[fake_response(503), fake_response(503), fake_response(payload=reply)]
        ):
            summary = feedback.summarise_attempt(test_title="T", level="", skills={"overall": 72}, answers=[answer])
        self.assertEqual(summary["summary"], "Good work.")


class ConnectionCheckTests(APITestCase):
    def setUp(self):
        admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha", role="admin")
        self.client.force_authenticate(admin)

    def check(self, responses):
        with mock.patch("apps.evaluation.checks.requests.post", side_effect=responses) as post:
            data = self.client.post(reverse("evaluation-check")).data["results"]
        return data, post

    @override_settings(**{**GROQ, **GEMINI, "EVALUATION_DEMO_MODE": True})
    def test_all_services_working_even_in_demo_mode(self):
        ok_chat = fake_response(payload=chat_payload('{"ok": true}'))
        data, post = self.check([fake_response(payload={"text": ""}), ok_chat, ok_chat])
        self.assertEqual([(r["step"], r["service"], r["status"]) for r in data], [
            ("Speech-to-text", "Groq", "ok"), ("Written feedback", "Groq", "ok"), ("Feedback backup", "Gemini", "ok"),
        ])
        speech = post.call_args_list[0]
        self.assertTrue(speech.args[0].endswith("/audio/transcriptions"))
        self.assertEqual(speech.kwargs["files"]["file"][2], "audio/wav")

    @override_settings(**GROQ)
    def test_rejected_key_and_free_limit_are_explained(self):
        data, _ = self.check([fake_response(401, payload={"error": {"message": "Invalid API Key"}}), fake_response(429)])
        self.assertEqual(data[0]["status"], "error")
        self.assertIn("GROQ_API_KEY", data[0]["detail"])
        self.assertEqual(data[1]["status"], "warning")
        self.assertIn("free limit", data[1]["detail"])
        self.assertEqual(len(data), 2)  # no backup configured

    @override_settings(**{**GROQ, "GROQ_API_KEY": ""})
    def test_missing_key_is_named_without_calling_anything(self):
        data, post = self.check([])
        self.assertEqual(post.call_count, 0)
        self.assertEqual(data[0]["detail"], "GROQ_API_KEY is not set.")

    @override_settings(**GROQ)
    def test_unreachable_service(self):
        import requests

        data, _ = self.check([requests.ConnectionError("down"), requests.ConnectionError("down")])
        self.assertIn("Couldn't reach Groq", data[0]["detail"])

    @override_settings(**GROQ)
    def test_unknown_model_is_explained(self):
        data, _ = self.check([fake_response(payload={"text": ""}), fake_response(404, payload={"error": {"message": "model not found"}})])
        self.assertIn("doesn't know the model", data[1]["detail"])

    def test_students_cannot_run_the_check(self):
        student = User.objects.create_user("aarati@example.com", "Speak-Clearly-2026", full_name="Aarati")
        self.client.force_authenticate(student)
        self.assertEqual(self.client.post(reverse("evaluation-check")).status_code, 403)


@override_settings(**{**GROQ, **GEMINI, "GEMINI_MODEL": "gemini-2.5-flash"})
class ModelSuggestionTests(APITestCase):
    def test_unknown_gemini_model_suggests_ones_the_key_can_use(self):
        admin = User.objects.create_user("nisha@example.com", "Speak-Clearly-2026", full_name="Nisha", role="admin")
        self.client.force_authenticate(admin)
        ok_chat = fake_response(payload=chat_payload('{"ok": true}'))
        listing = fake_response(payload={"data": [
            {"id": "models/gemini-3.5-flash-lite"}, {"id": "models/gemini-3.8-flash"}, {"id": "models/gemini-3.1-flash-live-preview"},
            {"id": "models/gemini-embedding-001"}, {"id": "models/gemini-3.6-flash"},
        ]})
        with mock.patch("apps.evaluation.checks.requests.post", side_effect=[fake_response(payload={"text": ""}), ok_chat, fake_response(404), fake_response(404)]), \
                mock.patch("apps.evaluation.checks.requests.get", return_value=listing) as get:
            rows = self.client.post(reverse("evaluation-check")).data["results"]
        backup = rows[2]
        self.assertEqual(backup["status"], "error")
        self.assertIn("gemini-3.8-flash, gemini-3.6-flash, gemini-3.5-flash-lite", backup["detail"])
        self.assertIn("GEMINI_MODEL", backup["detail"])
        self.assertNotIn("live-preview", backup["detail"])
        self.assertTrue(get.call_args.args[0].endswith("/v1beta/openai/models"))
