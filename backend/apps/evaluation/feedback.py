"""
Written feedback: the per-answer analysis and the attempt summary.
Anthropic Claude by default, or an open model on Groq's free tier when AI_PROVIDER=groq.

All text follows the product tone: plain, friendly and respectful, never sarcastic.
"""

import json
import logging
import time

import requests
from django.conf import settings

from apps.common.utils import clamp_score

from . import providers
from .speech_to_text import RETRY_STATUS_CODES, EvaluationError, EvaluationNotConfigured

logger = logging.getLogger(__name__)

ANTHROPIC_VERSION = "2023-06-01"
TONE_RULES = "Tone: plain, friendly and respectful. Never sarcastic, never joking, no slang, no emoji."

ANSWERS_QUESTION = ("yes", "partly", "no")
DEFAULT_TIP = "Try to speak for the full time and give one example to support your answer."
DEFAULT_NEXT_STEP = "Practise one short answer each day and listen back to your recording."

ANSWER_SYSTEM_PROMPT = "\n".join(
    [
        "You are a strict but fair English speaking examiner for the Voice Mock Test app.",
        "You get the question, an automatic transcript of a student's spoken answer, the speaking time allowed and speaking measurements.",
        "Judge only what the transcript shows. Ignore punctuation and capital letters, which come from the transcriber.",
        "Step 1. Decide if the answer responds to THIS question. answers_question is "
        '"yes" (it answers what was asked), "partly" (right topic but misses the main point or most of it) '
        'or "no" (off topic, a memorised text on another subject, or no real answer).',
        "Step 2. Score each item from 0 to 100 with these bands. Use the whole range: most learners score between 40 and 75. "
        "Never give a default score such as 70 or 75; every number must follow from the transcript.",
        "relevance: 85-100 answers every part of the question with details or examples; 60-84 answers it but briefly; "
        "30-59 only partly answers or drifts away; 0-29 off topic or no real answer.",
        "coherence: 85-100 clear order, well linked, developed; 60-84 mostly clear with simple linking; "
        "40-59 jumps between ideas or repeats; 0-39 hard to follow.",
        "grammar: 85-100 almost no errors and varied structures; 65-84 some errors but meaning is clear; "
        "45-64 frequent errors or only very simple sentences; 0-44 errors make the meaning hard to follow. "
        "Under 20 words there is too little evidence: grammar at most 50.",
        "pronunciation_estimate: a rough guess from words the transcriber seems to have misheard; 70 if there is no sign of a problem.",
        "An answer that does not respond to the question can still have good grammar, but relevance and coherence must be low.",
        "Reply with one JSON object and nothing else, in this shape:",
        '{"answers_question":"yes|partly|no","relevance_reason":"...","relevance":0-100,"coherence":0-100,"grammar":0-100,'
        '"pronunciation_estimate":0-100,"strengths":["..."],"tip":"...","corrections":[{"said":"...","better":"..."}]}',
        "relevance_reason: one short sentence saying how well the answer fits the question. "
        'strengths: one or two short sentences starting with "You" or "Your". '
        "tip: one practical sentence the student can act on next time; if the answer missed the question, the tip says what to talk about. "
        "corrections: at most two, quoting the student exactly.",
        TONE_RULES,
    ]
)

SUMMARY_SYSTEM_PROMPT = "\n".join(
    [
        "You are an English speaking coach for the Voice Mock Test app.",
        "You get a student's skill scores (0-100) and short notes on each answer from one speaking test.",
        "Reply with one JSON object and nothing else, in this shape:",
        '{"summary":"...","strengths":["...","..."],"tip":"...","next_step":"..."}',
        "summary: one or two sentences about how the test went overall. "
        'strengths: exactly two short sentences starting with "You" or "Your".',
        "tip: the single most useful thing to work on, as one practical sentence. "
        "next_step: one small practice activity for the next few days.",
        TONE_RULES,
    ]
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def analyse_answer(*, question: str, transcript: str, level: str, measurements: dict, time_limit: int | None = None) -> dict:
    """Whether the answer fits the question, plus grammar, coherence, strengths, tip and corrections."""
    if settings.EVALUATION_DEMO_MODE:
        return demo_analysis()

    user_content = json.dumps(
        {
            "question": question,
            "student_level": level or "not given",
            "speaking_time_allowed_seconds": time_limit,
            "transcript": transcript,
            "measurements": measurements,
        }
    )
    # Temperature 0: the same answer gets the same scores.
    reply = call_model(ANSWER_SYSTEM_PROMPT, user_content, max_tokens=900, temperature=0)
    if reply is None:
        raise EvaluationError()

    relevance = _score(reply.get("relevance"), 50)
    answers_question = str(reply.get("answers_question") or "").strip().lower()
    if answers_question not in ANSWERS_QUESTION:
        answers_question = "yes" if relevance >= 60 else "partly" if relevance >= 30 else "no"
    return {
        "answers_question": answers_question,
        "relevance_reason": _text(reply.get("relevance_reason"), 300),
        "grammar": _score(reply.get("grammar"), 50),
        "coherence": _score(reply.get("coherence"), 50),
        "relevance": relevance,
        "pronunciation_estimate": _score(reply.get("pronunciation_estimate"), 70),
        "strengths": _sentences(reply.get("strengths"), limit=2),
        "tip": _text(reply.get("tip")) or DEFAULT_TIP,
        "corrections": _corrections(reply.get("corrections")),
    }


def summarise_attempt(*, test_title: str, level: str, skills: dict, answers: list) -> dict:
    """Summary, two strengths, tip and next step for a finished test.

    Uses Claude when available and falls back to the per-answer feedback otherwise,
    so a result is always produced.
    """
    fallback = _fallback_summary(skills.get("overall"), answers)
    if settings.EVALUATION_DEMO_MODE:
        return fallback

    user_content = json.dumps(
        {
            "test": test_title,
            "student_level": level or "not given",
            "skills": skills,
            "answers": [
                {"question": a.question_text, "score": a.overall, "strengths": a.strengths, "tip": a.tip}
                for a in answers
            ],
        }
    )
    try:
        reply = call_model(SUMMARY_SYSTEM_PROMPT, user_content, max_tokens=600)
    except EvaluationError:
        logger.warning("Attempt summary unavailable; using fallback text.")
        return fallback
    if not reply:
        return fallback

    return {
        "summary": _text(reply.get("summary")) or fallback["summary"],
        "strengths": _sentences(reply.get("strengths"), limit=2) or fallback["strengths"],
        "tip": _text(reply.get("tip")) or fallback["tip"],
        "next_step": _text(reply.get("next_step")) or fallback["next_step"],
    }


def call_model(system: str, user_content: str, *, max_tokens: int = 800, temperature: float = 0.2):
    """Ask the feedback model and return the JSON object in its reply (or None).

    Tries the main service first; if it is busy, over its free limit, unreachable or not set up,
    the free Gemini backup (GEMINI_API_KEY) answers instead.
    """
    services = providers.feedback_services()
    last_error = None
    for position, service in enumerate(services):
        try:
            if service.kind == providers.ANTHROPIC:
                reply = call_claude(system, user_content, max_tokens=max_tokens, temperature=temperature)
            else:
                reply = call_chat_completions(service, system, user_content, max_tokens=max_tokens, temperature=temperature)
        except EvaluationError as exc:  # includes EvaluationNotConfigured
            last_error = exc
            reply = None
        if reply is not None:
            return reply
        if position + 1 < len(services):
            logger.warning("%s gave no usable feedback; trying %s instead.", service.name, services[position + 1].name)
    if last_error is not None:
        raise last_error
    return None


def chat_bodies(service, system: str, user_content: str, max_tokens: int, temperature: float = 0.2) -> tuple[dict, dict]:
    """The full request (JSON mode, low reasoning) and a basic one for services that refuse an option."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user_content}]
    basic = {"model": service.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens * 3}
    full = dict(basic, response_format={"type": "json_object"})
    if service.model.startswith("openai/gpt-oss") or service.name == "Gemini":
        full["reasoning_effort"] = "low"  # quicker answers and fewer tokens on free tiers
    return full, basic


def post_chat(service, body: dict):
    """One POST to an OpenAI-compatible /chat/completions endpoint."""
    return requests.post(
        f"{service.base_url}/chat/completions",
        headers={"Authorization": f"Bearer {service.api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=settings.AI_REQUEST_TIMEOUT,
    )


def call_chat_completions(service, system: str, user_content: str, *, max_tokens: int = 800, temperature: float = 0.2, tries: int = 2):
    """OpenAI-compatible chat API (Groq, Gemini). Returns the JSON object in the reply (or None)."""
    if not service.api_key:
        logger.error("%s is missing. Add it to backend/.env or set EVALUATION_DEMO_MODE=True.", service.key_setting)
        raise EvaluationNotConfigured()

    body, basic = chat_bodies(service, system, user_content, max_tokens, temperature)
    simplified = False
    for attempt in range(1, tries + 1):
        try:
            response = post_chat(service, body)
        except requests.RequestException as exc:
            logger.warning("%s feedback request failed (try %s): %s", service.name, attempt, exc)
            response = None

        if response is not None:
            if response.ok:
                return parse_chat_reply(response.json())
            logger.warning(
                "Feedback model returned %s from %s (try %s): %s", response.status_code, service.name, attempt, response.text[:300]
            )
            if response.status_code in (401, 403):
                raise EvaluationNotConfigured()
            if response.status_code == 400 and not simplified:
                # The model may not accept an optional setting: try again with the basic request.
                body, simplified = basic, True
                continue
            if response.status_code not in RETRY_STATUS_CODES:
                break
        if attempt < tries:
            time.sleep(2)

    raise EvaluationError()


def parse_chat_reply(payload: dict):
    """Pull the JSON object out of a chat-completions response."""
    try:
        text = payload["choices"][0]["message"].get("content") or ""
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
    return _json_object(text)


def call_claude(system: str, user_content: str, *, max_tokens: int = 800, temperature: float = 0.2, tries: int = 2):
    """Send one message to Claude and return the JSON object in its reply (or None)."""
    if not settings.ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY is missing. Add it to backend/.env or set EVALUATION_DEMO_MODE=True.")
        raise EvaluationNotConfigured()

    url = f"{settings.ANTHROPIC_BASE_URL}/v1/messages"
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    body = {
        "model": settings.SCORING_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": user_content}],
    }

    for attempt in range(1, tries + 1):
        try:
            response = requests.post(url, headers=headers, json=body, timeout=settings.AI_REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            logger.warning("Claude request failed (try %s): %s", attempt, exc)
            response = None

        if response is not None:
            if response.ok:
                return parse_json_reply(response.json())
            logger.warning("Claude returned %s (try %s): %s", response.status_code, attempt, response.text[:300])
            if response.status_code in (401, 403):
                raise EvaluationNotConfigured()
            if response.status_code not in RETRY_STATUS_CODES:
                break
        if attempt < tries:
            time.sleep(2)

    raise EvaluationError()


def parse_json_reply(payload: dict):
    """Pull the first JSON object out of a Messages API response."""
    text = "".join(
        block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"
    )
    return _json_object(text)


def _json_object(text: str):
    """The first {...} object in a model's reply, or None."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _score(value, default: int) -> int:
    score = clamp_score(value)
    return default if score is None else score


def _text(value, max_length: int = 400) -> str:
    return " ".join(value.split())[:max_length] if isinstance(value, str) else ""


def _sentences(value, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for text in (_text(item, 200) for item in value) if text][:limit]


def _corrections(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    items = []
    for item in value:
        if isinstance(item, dict) and _text(item.get("said")) and _text(item.get("better")):
            items.append({"said": _text(item["said"], 200), "better": _text(item["better"], 200)})
    return items[:2]


def _fallback_summary(overall, answers) -> dict:
    if overall is None:
        summary = "Your answers have been saved."
    elif overall >= 80:
        summary = "You spoke clearly and confidently. You're making great progress."
    elif overall >= 60:
        summary = "You are improving. Keep practising a little every day."
    else:
        summary = "Every test helps. Keep practising and your scores will rise."

    strengths = []
    for answer in answers:
        for sentence in answer.strengths or []:
            if sentence not in strengths:
                strengths.append(sentence)
    tip = next((answer.tip for answer in answers if answer.tip), DEFAULT_TIP)
    return {"summary": summary, "strengths": strengths[:2], "tip": tip, "next_step": DEFAULT_NEXT_STEP}


def demo_analysis() -> dict:
    return {
        "answers_question": "yes",
        "relevance_reason": "The answer describes a favourite place and explains why.",
        "grammar": 74,
        "coherence": 78,
        "relevance": 86,
        "pronunciation_estimate": 72,
        "strengths": [
            "You answered the question directly and gave clear reasons.",
            "Your ideas follow a logical order.",
        ],
        "tip": 'Replace filler words like "um" with a short, silent pause.',
        "corrections": [
            {
                "said": "I go there in the evening",
                "better": "I usually go there in the evening",
            }
        ],
    }
