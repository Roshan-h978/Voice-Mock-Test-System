"""
Which AI service does each scoring step, chosen with AI_PROVIDER in backend/.env:

- "groq"   (free tier): one Groq key for speech-to-text (Whisper) and written feedback (an open model).
- "openai" (paid):      OpenAI speech-to-text and Anthropic Claude feedback, two keys.

Optional free backup: with GEMINI_API_KEY set, Google Gemini writes the feedback whenever the main
feedback service is busy, over its free limit or unreachable.
"""

from dataclasses import dataclass

from django.conf import settings

OPENAI_CHAT = "openai_chat"  # OpenAI-compatible /chat/completions (Groq, Gemini)
ANTHROPIC = "anthropic"  # Anthropic Messages API


@dataclass(frozen=True)
class Service:
    name: str  # shown on the admin dashboard
    base_url: str
    api_key: str
    model: str
    key_setting: str  # the setting to fill in when the key is missing
    kind: str = OPENAI_CHAT


def uses_groq() -> bool:
    return settings.AI_PROVIDER == "groq"


def speech_to_text() -> Service:
    if uses_groq():
        return Service("Groq", settings.GROQ_BASE_URL, settings.GROQ_API_KEY, settings.GROQ_TRANSCRIBE_MODEL, "GROQ_API_KEY")
    return Service("OpenAI", settings.OPENAI_BASE_URL, settings.OPENAI_API_KEY, settings.TRANSCRIBE_MODEL, "OPENAI_API_KEY")


def feedback() -> Service:
    """The main feedback service."""
    if uses_groq():
        return Service("Groq", settings.GROQ_BASE_URL, settings.GROQ_API_KEY, settings.GROQ_SCORING_MODEL, "GROQ_API_KEY")
    return Service(
        "Anthropic", settings.ANTHROPIC_BASE_URL, settings.ANTHROPIC_API_KEY, settings.SCORING_MODEL, "ANTHROPIC_API_KEY", ANTHROPIC
    )


def feedback_backup() -> Service | None:
    """Google Gemini (free tier), used only when GEMINI_API_KEY is set."""
    if not settings.GEMINI_API_KEY:
        return None
    return Service("Gemini", settings.GEMINI_BASE_URL, settings.GEMINI_API_KEY, settings.GEMINI_MODEL, "GEMINI_API_KEY")


def feedback_services() -> list[Service]:
    """Main feedback service first, then the backup (if any)."""
    backup = feedback_backup()
    return [feedback()] + ([backup] if backup else [])
