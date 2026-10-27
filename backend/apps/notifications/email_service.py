"""
Outgoing email for the Voice Mock Test System.

EMAIL_DELIVERY=django  Django sends every email with the SMTP settings in backend/.env.
EMAIL_DELIVERY=n8n     Invitations and password resets are posted to the n8n webhooks
                       (automation/workflows/invitation-email.json and password-reset-email.json).
Review results and test emails are always sent by Django.
"""

import logging
from html import escape

import requests
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.common.utils import frontend_url

logger = logging.getLogger(__name__)

COLORS = {
    "navy": "#142B4A",
    "teal": "#16A6A1",
    "muted": "#5B6B82",
    "border": "#DCE3EC",
    "page": "#F5F8FB",
}


class EmailDeliveryError(Exception):
    """The email could not be handed to SMTP or n8n."""


# ---------------------------------------------------------------------------
# Rendering and sending
# ---------------------------------------------------------------------------
def render_email(*, heading, paragraphs, button_label=None, button_url=None, note=None) -> tuple[str, str]:
    """Matching HTML and plain-text bodies in the product's Navy & Teal style."""
    c = COLORS
    body = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:22px;color:{c["navy"]}">{escape(text)}</p>'
        for text in paragraphs
    )
    button = ""
    if button_label and button_url:
        button = (
            f'<p style="margin:22px 0"><a href="{escape(button_url)}" '
            f'style="background:{c["teal"]};color:{c["navy"]};text-decoration:none;font-weight:600;'
            f'padding:12px 20px;border-radius:8px;display:inline-block">{escape(button_label)}</a></p>'
            f'<p style="margin:0 0 14px;font-size:13px;color:{c["muted"]}">If the button doesn\'t work, '
            f'copy this link into your browser:<br>{escape(button_url)}</p>'
        )
    footer = f'<p style="margin:18px 0 0;font-size:13px;color:{c["muted"]}">{escape(note)}</p>' if note else ""
    html = (
        f'<div style="background:{c["page"]};padding:24px;font-family:Inter,Segoe UI,Arial,sans-serif">'
        f'<div style="max-width:560px;margin:0 auto;background:#ffffff;border:1px solid {c["border"]};'
        f'border-radius:12px;padding:28px">'
        f'<p style="margin:0 0 6px;font-size:12px;font-weight:700;letter-spacing:.08em;color:{c["teal"]}">VOICE MOCK TEST</p>'
        f'<h1 style="margin:0 0 18px;font-size:22px;line-height:30px;color:{c["navy"]}">{escape(heading)}</h1>'
        f"{body}{button}{footer}</div></div>"
    )

    lines = [heading, "", *paragraphs]
    if button_label and button_url:
        lines += ["", f"{button_label}: {button_url}"]
    if note:
        lines += ["", note]
    return html, "\n".join(lines)


def send_email(*, to, subject, heading, paragraphs, button_label=None, button_url=None, note=None) -> None:
    html, text = render_email(
        heading=heading, paragraphs=paragraphs, button_label=button_label, button_url=button_url, note=note
    )
    recipients = [to] if isinstance(to, str) else list(to)
    message = EmailMultiAlternatives(subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=recipients)
    message.attach_alternative(html, "text/html")
    try:
        message.send(fail_silently=False)
    except Exception as exc:  # noqa: BLE001 - SMTP raises many different errors
        logger.exception("Email to %s failed", recipients)
        raise EmailDeliveryError("The email could not be sent.") from exc


def _send_with_n8n(webhook_path: str, payload: dict) -> None:
    url = f"{settings.N8N_WEBHOOK_BASE_URL}/{webhook_path}"
    try:
        response = requests.post(
            url, json=payload, headers={"X-Automation-Key": settings.AUTOMATION_API_KEY}, timeout=15
        )
    except requests.RequestException as exc:
        logger.exception("n8n webhook %s could not be reached", url)
        raise EmailDeliveryError("The email service could not be reached.") from exc
    if not response.ok:
        logger.error("n8n webhook %s returned %s: %s", url, response.status_code, response.text[:300])
        raise EmailDeliveryError("The email service returned an error.")


def _when(value) -> str:
    return timezone.localtime(value).strftime("%d %b %Y, %I:%M %p")


def _first_name(name: str) -> str:
    return name.split(" ")[0] if name else ""


# ---------------------------------------------------------------------------
# Emails
# ---------------------------------------------------------------------------
def send_invitation(*, email, name, role, link, invited_by, expires_at) -> None:
    if settings.EMAIL_DELIVERY == "n8n":
        _send_with_n8n(
            "vmt/invitation-email",
            {
                "email": email,
                "name": name,
                "role": role,
                "link": link,
                "invited_by": invited_by,
                "expires_at": expires_at.isoformat(),
                "expires_text": _when(expires_at),
            },
        )
        return

    purpose = "help manage Voice Mock Test as an admin" if role == "admin" else "practise English speaking on Voice Mock Test"
    send_email(
        to=email,
        subject="You're invited to Voice Mock Test",
        heading="You're invited",
        paragraphs=[
            f"Hi {_first_name(name)}," if name else "Hi,",
            f"{invited_by} has invited you to {purpose}.",
            f"Set up your account with the button below. The link works until {_when(expires_at)}.",
        ],
        button_label="Set up my account",
        button_url=link,
        note="If you weren't expecting this invitation, you can ignore this email.",
    )


def send_password_reset(*, email, name, link, expires_at) -> None:
    if settings.EMAIL_DELIVERY == "n8n":
        _send_with_n8n(
            "vmt/password-reset-email",
            {
                "email": email,
                "name": name,
                "link": link,
                "expires_at": expires_at.isoformat(),
                "expires_text": _when(expires_at),
            },
        )
        return

    send_email(
        to=email,
        subject="Reset your Voice Mock Test password",
        heading="Reset your password",
        paragraphs=[
            f"Hi {_first_name(name)}," if name else "Hi,",
            "We received a request to reset your password.",
            f"Choose a new password with the button below. The link works until {_when(expires_at)}.",
        ],
        button_label="Set a new password",
        button_url=link,
        note="If you didn't ask to reset your password, you can ignore this email. Your password won't change.",
    )


def send_review_published(attempt) -> None:
    student = attempt.student
    reviewer = attempt.reviewer.full_name if attempt.reviewer else "Your teacher"
    paragraphs = [
        f"Hi {_first_name(student.full_name)},",
        f"{reviewer} has reviewed your {attempt.test.title} test. Your score is {attempt.overall}%.",
    ]
    if attempt.reviewer_note:
        paragraphs.append(f"Note from your teacher: {attempt.reviewer_note}")
    if attempt.tip:
        paragraphs.append(f"Tip for next time: {attempt.tip}")
    send_email(
        to=student.email,
        subject=f"Your {attempt.test.title} test has been reviewed",
        heading="Your test has been reviewed",
        paragraphs=paragraphs,
        button_label="See my results",
        button_url=frontend_url(f"/student/results/{attempt.id}"),
    )


def send_test_email(to: str) -> None:
    send_email(
        to=to,
        subject="Voice Mock Test email check",
        heading="Email is working",
        paragraphs=["This is a test message from Voice Mock Test. Your email settings are working."],
    )
