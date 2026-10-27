"""
Sign in with Google.

The React app shows Google's own button (Google Identity Services). After the person
picks their Google account, the app sends the ID token ("credential") here. We check
it with Google's public keys, then sign in the matching user or create a student.
"""

import logging

from django.conf import settings
from google.auth import exceptions as google_exceptions
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from apps.common.utils import ServiceError

from .models import AccountToken, User

logger = logging.getLogger(__name__)

GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
FAILED = "Google sign-in didn't work. Please try again."


def is_enabled() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID)


def verify_credential(credential: str) -> dict:
    """Check the ID token's signature, audience, issuer and expiry. Returns its claims."""
    if not is_enabled():
        raise ServiceError("Google sign-in isn't set up yet.", status_code=503)
    try:
        claims = id_token.verify_token(
            credential,
            google_requests.Request(),
            audience=settings.GOOGLE_CLIENT_ID,
            certs_url=settings.GOOGLE_CERTS_URL,
            clock_skew_in_seconds=10,
        )
    except google_exceptions.TransportError as exc:
        logger.warning("Could not reach Google to check a sign-in: %s", exc)
        raise ServiceError("We couldn't reach Google. Please try again.", status_code=502) from exc
    except (ValueError, google_exceptions.GoogleAuthError) as exc:
        logger.info("Rejected Google credential: %s", exc)
        raise ServiceError(FAILED, status_code=401) from exc

    if claims.get("iss") not in GOOGLE_ISSUERS:
        raise ServiceError(FAILED, status_code=401)
    if not claims.get("email") or not claims.get("email_verified"):
        raise ServiceError("Your Google account's email address isn't verified.", status_code=401)
    return claims


def user_for_claims(claims: dict, invite_token: str = "") -> tuple[User, bool]:
    """Return (user, created). Existing accounts are matched by email."""
    email = claims["email"].strip().lower()
    user = User.objects.filter(email__iexact=email).first()
    if user:
        if not user.is_active:
            raise ServiceError("This account is suspended. Please contact your teacher.", status_code=403)
        return user, False

    invitation = None
    if invite_token:
        invitation = AccountToken.find_valid(invite_token, AccountToken.INVITATION_PURPOSES)
        if invitation and invitation.email != email:
            raise ServiceError(
                f"Use the Google account for {invitation.email}, the address the invitation was sent to.",
                status_code=400,
            )
    if invitation is None and not settings.ALLOW_PUBLIC_REGISTRATION:
        raise ServiceError("Sign-up is by invitation only. Ask your teacher for an invitation.", status_code=403)

    name = " ".join(str(claims.get("name") or "").split()) or email.split("@")[0]
    user = User.objects.create_user(
        email=email,
        password=None,  # Google accounts sign in with Google; "Forgot password" can add a password later
        full_name=name[:150],
        role=invitation.role if invitation else User.Role.STUDENT,
    )
    if invitation:
        invitation.mark_used()
    return user, True
