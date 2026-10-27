"""Small helpers shared by every app."""

import hashlib
import secrets
from datetime import date, datetime, time, timedelta
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework.exceptions import APIException, NotFound
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import exception_handler

AUDIO_EXTENSIONS = {".webm", ".ogg", ".oga", ".mp3", ".mpga", ".mpeg", ".m4a", ".mp4", ".wav", ".flac"}
AUDIO_CONTAINER_TYPES = {"video/webm", "video/mp4", "video/ogg", "application/ogg"}
CONTENT_TYPE_EXTENSIONS = {
    "audio/webm": ".webm",
    "video/webm": ".webm",
    "audio/ogg": ".ogg",
    "application/ogg": ".ogg",
    "audio/mp4": ".m4a",
    "audio/x-m4a": ".m4a",
    "video/mp4": ".mp4",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/x-wav": ".wav",
    "audio/wave": ".wav",
    "audio/flac": ".flac",
}


# ---------------------------------------------------------------------------
# API errors and pagination
# ---------------------------------------------------------------------------
class ServiceError(APIException):
    """A business-rule error with a plain message, returned as {"detail": "..."}."""

    status_code = 400
    default_detail = "This request could not be completed."
    default_code = "invalid"

    def __init__(self, detail=None, status_code=None, code=None):
        super().__init__(detail, code)
        if status_code is not None:
            self.status_code = status_code


NOT_FOUND_MESSAGE = "We couldn't find what you were looking for. It may have been removed, or the link may be wrong."


def api_exception_handler(exc, context):
    """DRF's error handler, with a plain message instead of Django's "No Attempt matches the given query."."""
    if isinstance(exc, Http404):
        exc = NotFound(NOT_FOUND_MESSAGE)
    return exception_handler(exc, context)


class StandardPagination(PageNumberPagination):
    """Page-number pagination that also accepts ?page_size= (up to 100)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# ---------------------------------------------------------------------------
# Tokens and links
# ---------------------------------------------------------------------------
def generate_token(nbytes: int = 32) -> str:
    """Random hex token (64 characters by default)."""
    return secrets.token_hex(nbytes)


def hash_token(raw: str) -> str:
    """SHA-256 hash of a token, so only hashes are stored in the database."""
    return hashlib.sha256(raw.encode()).hexdigest()


def frontend_url(path: str, **params) -> str:
    """Absolute link to a page of the React app, e.g. frontend_url("/reset-password", token=t)."""
    url = f"{settings.FRONTEND_URL}/{path.lstrip('/')}"
    query = {key: value for key, value in params.items() if value not in (None, "")}
    return f"{url}?{urlencode(query)}" if query else url


# ---------------------------------------------------------------------------
# Numbers and scores
# ---------------------------------------------------------------------------
def clamp_score(value, low: int = 0, high: int = 100):
    """Round a number and keep it between low and high. None stays None."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(max(low, min(high, round(number))))


def average(values):
    """Rounded average of the numbers in values, ignoring None. None when there are none."""
    numbers = [value for value in values if value is not None]
    return clamp_score(sum(numbers) / len(numbers)) if numbers else None


def weighted_average(values: dict, weights: dict):
    """Weighted average of the keys present in both dicts, ignoring None values."""
    present = {key: value for key, value in values.items() if value is not None and weights.get(key)}
    total_weight = sum(weights[key] for key in present)
    if not total_weight:
        return None
    return clamp_score(sum(value * weights[key] for key, value in present.items()) / total_weight)


def percent_change(current, previous):
    """Whole-number percentage change, or None when there is nothing to compare with."""
    if not previous or current is None:
        return None
    return round((current - previous) / previous * 100)


# ---------------------------------------------------------------------------
# Audio uploads
# ---------------------------------------------------------------------------
def _content_type(upload) -> str:
    return (getattr(upload, "content_type", "") or "").split(";")[0].strip().lower()


def validate_audio_upload(upload):
    """Return a friendly error message for an unusable recording, or None when it is fine."""
    if upload is None:
        return "Attach the recording as 'audio'."
    if upload.size == 0:
        return "The recording is empty. Please record your answer again."
    if upload.size > settings.MAX_AUDIO_UPLOAD_MB * 1024 * 1024:
        return f"The recording is larger than {settings.MAX_AUDIO_UPLOAD_MB} MB. Please record a shorter answer."
    content_type = _content_type(upload)
    extension = Path(upload.name or "").suffix.lower()
    if content_type.startswith("audio/") or content_type in AUDIO_CONTAINER_TYPES or extension in AUDIO_EXTENSIONS:
        return None
    return "Unsupported audio type. Record in the browser or upload a webm, ogg, mp3, m4a, mp4 or wav file."


def audio_extension(upload) -> str:
    """File extension for a recording, from its name or content type (speech-to-text needs it)."""
    extension = Path(upload.name or "").suffix.lower()
    if extension in AUDIO_EXTENSIONS:
        return extension
    return CONTENT_TYPE_EXTENSIONS.get(_content_type(upload), ".webm")


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def _safe_date(value):
    try:
        parsed = parse_date(value or "")
    except ValueError:
        return None
    # Days at the very ends of the calendar (0001-01-01, 9999-12-31) can't become a time range.
    return parsed if parsed and date(1900, 1, 1) <= parsed <= date(2999, 12, 31) else None


def parse_date_range(params, default_days: int = 30):
    """Read ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD from query params.

    Returns (start, end, start_date, end_date): start is inclusive and end is exclusive,
    both timezone-aware. Defaults to the last `default_days` days.
    """
    end_date = _safe_date(params.get("date_to")) or timezone.localdate()
    start_date = _safe_date(params.get("date_from")) or end_date - timedelta(days=default_days - 1)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(start_date, time.min), tz)
    end = timezone.make_aware(datetime.combine(end_date + timedelta(days=1), time.min), tz)
    return start, end, start_date, end_date
