"""Creating in-app notifications. Never lets a notification problem break the action that caused it."""

import logging

from django.contrib.auth import get_user_model

from .models import Notification

logger = logging.getLogger(__name__)
User = get_user_model()


def review_published(attempt) -> None:
    """Tell the student their teacher has reviewed a test."""
    _safe(
        lambda: Notification.objects.create(
            user=attempt.student,
            kind=Notification.Kind.REVIEW_PUBLISHED,
            title=f"Your teacher reviewed “{attempt.test.title}”",
            body=f"Your score is now {attempt.overall}%." if attempt.overall is not None else "",
            link=f"/student/results/{attempt.pk}",
            attempt=attempt,
        )
    )


def test_published(test) -> None:
    """Tell every active student about a newly published test."""
    students = User.objects.filter(role=User.Role.STUDENT, is_active=True, is_superuser=False).only("id")
    _safe(
        lambda: Notification.objects.bulk_create(
            [
                Notification(
                    user=student,
                    kind=Notification.Kind.TEST_PUBLISHED,
                    title=f"New test: “{test.title}”",
                    body=f"{test.get_level_display()} level. Try it when you're ready.",
                    link=f"/student/tests/{test.pk}",
                    test=test,
                )
                for student in students
            ],
            batch_size=500,
        )
    )


def review_needed(attempt) -> None:
    """Tell every active admin that a finished test was flagged for review."""
    admins = User.objects.filter(is_active=True).filter(role=User.Role.ADMIN).only("id")
    reason = (attempt.review_reasons or [""])[0]
    _safe(
        lambda: Notification.objects.bulk_create(
            [
                Notification(
                    user=admin,
                    kind=Notification.Kind.REVIEW_NEEDED,
                    title=f"{attempt.student.full_name}'s test needs a review",
                    body=f"{attempt.test.title}. {reason}".strip(),
                    link=f"/admin/reviews/{attempt.pk}",
                    attempt=attempt,
                )
                for admin in admins
            ]
        )
    )


def _safe(create) -> None:
    try:
        create()
    except Exception:  # noqa: BLE001 - the review, test or result itself must still be saved
        logger.exception("Could not create a notification")
