"""
Speech-to-text for recorded answers, using the OpenAI transcription API.

The errors shared by the whole evaluation pipeline are defined here, because
transcription is its first step.
"""

import logging
import time
from dataclasses import dataclass, field

import requests
from django.conf import settings

from apps.common.utils import ServiceError

logger = logging.getLogger(__name__)

RETRY_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504, 529}


# ---------------------------------------------------------------------------
# Errors (shown to the student as {"detail": "..."})
# ---------------------------------------------------------------------------
class EvaluationError(ServiceError):
    status_code = 502
    default_detail = "The scoring service is busy right now. Please submit your answer again."
    default_code = "evaluation_failed"


class EvaluationNotConfigured(EvaluationError):
    status_code = 503
    default_detail = "Speech scoring is not set up yet. Please tell your teacher."
    default_code = "evaluation_not_configured"


class NoSpeechDetected(EvaluationError):
    status_code = 422
    default_detail = "We could not hear any speech in this recording. Check your microphone and record the answer again."
    default_code = "no_speech"


# ---------------------------------------------------------------------------
# Transcript data
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    start: float
    end: float
    text: str
    avg_logprob: float | None = None
    no_speech_prob: float | None = None


@dataclass
class Transcript:
    text: str
    duration: float | None = None
    segments: list[Segment] = field(default_factory=list)
    is_demo: bool = False

    @property
    def words(self) -> list[str]:
        return [word for word in self.text.split() if any(char.isalnum() for char in word)]


def _number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def transcribe(audio, *, filename: str = "answer.webm", content_type: str = "audio/webm") -> Transcript:
    """Turn a recording (any file-like object) into text with segment timings."""
    if settings.EVALUATION_DEMO_MODE:
        return demo_transcript()
    if not settings.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is missing. Add it to backend/.env or set EVALUATION_DEMO_MODE=True.")
        raise EvaluationNotConfigured()

    model = settings.TRANSCRIBE_MODEL
    verbose = model.startswith("whisper")  # only whisper models return segment timings
    data = {
        "model": model,
        "language": "en",
        "temperature": "0",
        "response_format": "verbose_json" if verbose else "json",
    }
    if verbose:
        data["timestamp_granularities[]"] = "segment"

    payload = _request_transcription(audio, filename, content_type, data)
    segments = [
        Segment(
            start=_number(item.get("start")) or 0.0,
            end=_number(item.get("end")) or 0.0,
            text=str(item.get("text") or "").strip(),
            avg_logprob=_number(item.get("avg_logprob")),
            no_speech_prob=_number(item.get("no_speech_prob")),
        )
        for item in payload.get("segments") or []
    ]
    transcript = Transcript(
        text=" ".join(str(payload.get("text") or "").split()),
        duration=_number(payload.get("duration")),
        segments=segments,
    )
    if len(transcript.words) < 2:
        raise NoSpeechDetected()
    return transcript


def _request_transcription(audio, filename, content_type, data, tries: int = 2) -> dict:
    url = f"{settings.OPENAI_BASE_URL}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}

    for attempt in range(1, tries + 1):
        audio.seek(0)
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                files={"file": (filename, audio, content_type)},
                timeout=settings.AI_REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            logger.warning("Transcription request failed (try %s): %s", attempt, exc)
            response = None

        if response is not None:
            if response.ok:
                return response.json()
            logger.warning("Transcription returned %s (try %s): %s", response.status_code, attempt, response.text[:300])
            if response.status_code in (401, 403):
                raise EvaluationNotConfigured()
            if response.status_code == 400:
                raise EvaluationError(
                    "We couldn't read this recording. Please record your answer again.", status_code=422
                )
            if response.status_code not in RETRY_STATUS_CODES:
                break
        if attempt < tries:
            time.sleep(2)

    raise EvaluationError()


# ---------------------------------------------------------------------------
# Demo mode (EVALUATION_DEMO_MODE=True): realistic sample without any API call
# ---------------------------------------------------------------------------
DEMO_SENTENCES = [
    "My favourite place is the small park near my home.",
    "I go there in the evening because it is quiet and I can relax after college.",
    "There is a lake and many trees, so the air feels fresh.",
    "Um, sometimes I meet my friends there and we talk about our day.",
    "I enjoy it because it helps me feel calm and ready for the next day.",
]


def demo_transcript() -> Transcript:
    segments, clock = [], 0.4
    for index, sentence in enumerate(DEMO_SENTENCES):
        length = round(len(sentence.split()) / 2.2, 2)  # about 132 words a minute
        segments.append(Segment(clock, clock + length, sentence, avg_logprob=-0.18, no_speech_prob=0.02))
        clock += length + (1.8 if index == 2 else 0.5)  # one long pause after the third sentence
    return Transcript(text=" ".join(DEMO_SENTENCES), duration=round(clock, 1), segments=segments, is_demo=True)
