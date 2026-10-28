"""
"Test AI connection" for the admin dashboard: one small real request to each AI service,
reported as plain sentences. Works in demo mode too, so keys can be checked before switching it off.
"""

import io
import math
import struct
import wave

import requests
from django.conf import settings

from . import providers
from .feedback import ANTHROPIC_VERSION, chat_bodies, parse_chat_reply, post_chat
from .speech_to_text import transcription_fields

PING_SYSTEM = "You check that an API connection works. Reply with one JSON object and nothing else."
PING_USER = 'Reply with exactly this JSON: {"ok": true}'


def run_all() -> list[dict]:
    results = [check_speech_to_text()]
    results.append(check_feedback(providers.feedback(), "Written feedback"))
    backup = providers.feedback_backup()
    if backup:
        results.append(check_feedback(backup, "Feedback backup"))
    return results


def check_speech_to_text() -> dict:
    service = providers.speech_to_text()
    result = _base("Speech-to-text", service)
    if not service.api_key:
        return _fail(result, f"{service.key_setting} is not set.")
    try:
        response = requests.post(
            f"{service.base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {service.api_key}"},
            data=transcription_fields(service),
            files={"file": ("check.wav", io.BytesIO(_tone_wav()), "audio/wav")},
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        return _fail(result, f"Couldn't reach {service.name}. Check the server's internet connection.")
    return _from_response(result, service, response)


def check_feedback(service, step: str) -> dict:
    result = _base(step, service)
    if not service.api_key:
        return _fail(result, f"{service.key_setting} is not set.")
    try:
        if service.kind == providers.ANTHROPIC:
            response = requests.post(
                f"{service.base_url}/v1/messages",
                headers={"x-api-key": service.api_key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"},
                json={"model": service.model, "max_tokens": 50, "system": PING_SYSTEM, "messages": [{"role": "user", "content": PING_USER}]},
                timeout=settings.AI_REQUEST_TIMEOUT,
            )
        else:
            full, basic = chat_bodies(service, PING_SYSTEM, PING_USER, max_tokens=200)
            response = post_chat(service, full)
            if response.status_code == 400:  # the same fallback the real scoring uses
                response = post_chat(service, basic)
    except requests.RequestException:
        return _fail(result, f"Couldn't reach {service.name}. Check the server's internet connection.")
    result = _from_response(result, service, response)
    if result["status"] == "ok" and service.kind != providers.ANTHROPIC and parse_chat_reply(_json(response)) is None:
        result.update(status="warning", detail="Connected, but the model's reply wasn't in the expected format. Try another model.")
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _base(step, service) -> dict:
    return {"step": step, "service": service.name, "model": service.model, "status": "error", "detail": ""}


def _fail(result, detail) -> dict:
    result.update(status="error", detail=detail)
    return result


def _json(response) -> dict:
    try:
        data = response.json()
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def _error_text(response) -> str:
    data = _json(response)
    error = data.get("error")
    message = error.get("message") if isinstance(error, dict) else error if isinstance(error, str) else ""
    if not message and isinstance(data, dict):
        message = data.get("message") or ""
    return " ".join(str(message).split())[:200]


def _from_response(result, service, response) -> dict:
    code = response.status_code
    if 200 <= code < 300:
        result.update(status="ok", detail="Connected and working.")
    elif code in (401, 403):
        _fail(result, f"{service.name} rejected the key. Check {service.key_setting}.")
    elif code == 404:
        _fail(result, f"{service.name} doesn't know the model “{service.model}”. Check the model name.")
    elif code == 429:
        result.update(status="warning", detail="The key works, but the free limit is used up for now. Try again in a minute.")
    else:
        message = _error_text(response)
        _fail(result, f"{service.name} answered with error {code}." + (f" {message}" if message else ""))
    return result


def _tone_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """A short, quiet tone: enough for a speech-to-text service to accept the upload."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(rate)
        frames = (struct.pack("<h", int(3000 * math.sin(2 * math.pi * 440 * i / rate))) for i in range(int(seconds * rate)))
        audio.writeframes(b"".join(frames))
    return buffer.getvalue()
