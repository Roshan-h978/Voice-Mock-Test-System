"""Rate limits for requests that use the AI service (its free tier has daily limits)."""

from rest_framework.throttling import UserRateThrottle


class AIWriteThrottle(UserRateThrottle):
    """Asking the AI to write questions (admins and Quick practice). THROTTLE_AI in settings."""

    scope = "ai"


class PracticeThrottle(UserRateThrottle):
    """Scoring Quick practice answers. THROTTLE_PRACTICE in settings."""

    scope = "practice"
