"""
Business logic for test attempts: start, answer, submit, review and rescore,
plus the numbers behind the dashboards, reports and n8n automations.
"""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Max, Min, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.common.utils import (
    ServiceError,
    audio_extension,
    clamp_score,
    frontend_url,
    percent_change,
    validate_audio_upload,
)
from apps.evaluation import feedback, scoring
from apps.notifications import email_service
from apps.tests_manager.models import MockTest

from .models import FINISHED_STATUSES, Answer, Attempt

logger = logging.getLogger(__name__)
User = get_user_model()


# ---------------------------------------------------------------------------
# Taking a test
# ---------------------------------------------------------------------------
def start_attempt(student, test: MockTest) -> tuple[Attempt, bool]:
    """Start a test, or resume the student's unfinished attempt. Returns (attempt, created)."""
    if test.status != MockTest.Status.PUBLISHED:
        raise ServiceError("This test is not available right now.", status_code=404)
    if not test.questions.exists():
        raise ServiceError("This test has no questions yet.", status_code=409)

    current = Attempt.objects.filter(student=student, test=test, status=Attempt.Status.IN_PROGRESS).first()
    if current:
        return current, False

    already_done = Attempt.objects.filter(student=student, test=test, status__in=FINISHED_STATUSES).exists()
    if already_done and not test.allow_retake:
        raise ServiceError("You have already completed this test.", status_code=409)

    return Attempt.objects.create(student=student, test=test), True


def save_answer(attempt: Attempt, question, audio, recorded_seconds=None) -> Answer:
    """Score a recording and save it. Recording a question again replaces the earlier answer."""
    if attempt.status != Attempt.Status.IN_PROGRESS:
        raise ServiceError("This test is already finished.", status_code=409)
    if question.test_id != attempt.test_id:
        raise ServiceError("This question is not part of the test.")
    error = validate_audio_upload(audio)
    if error:
        raise ServiceError(error)

    extension = audio_extension(audio)
    result = scoring.evaluate_answer(
        audio,
        question_text=question.text,
        level=attempt.student.level,
        recorded_seconds=recorded_seconds,
        filename=f"answer{extension}",
        content_type=(audio.content_type or "audio/webm").split(";")[0],
    )

    answer = Answer.objects.filter(attempt=attempt, question=question).first() or Answer(
        attempt=attempt, question=question
    )
    old_audio_name = answer.audio.name if answer.pk and answer.audio else ""

    answer.question_order = question.order
    answer.question_text = question.text
    for field, value in result.as_model_fields().items():
        setattr(answer, field, value)
    if recorded_seconds:
        answer.duration_seconds = round(float(recorded_seconds), 1)

    audio.seek(0)
    answer.audio.save(f"answer{extension}", audio, save=False)
    answer.save()

    if old_audio_name and old_audio_name != answer.audio.name:
        _delete_file(answer.audio.storage, old_audio_name)
    return answer


def submit_attempt(attempt: Attempt) -> Attempt:
    """Finish a test: combine the answer scores, write the summary and flag it for review if needed."""
    if attempt.is_finished:
        return attempt

    answers = list(attempt.answers.all())
    if not answers:
        raise ServiceError("Record at least one answer before finishing the test.")
    question_ids = set(attempt.test.questions.values_list("id", flat=True))
    missing = question_ids - {answer.question_id for answer in answers}
    if missing:
        left = len(missing)
        raise ServiceError(f"Answer every question before finishing. {left} question{'s' if left != 1 else ''} left.")

    _apply_scores(attempt, answers)
    summary = feedback.summarise_attempt(
        test_title=attempt.test.title,
        level=attempt.student.level,
        skills={skill: getattr(attempt, skill) for skill in (*scoring.SKILLS, "overall")},
        answers=answers,
    )
    attempt.summary = summary["summary"]
    attempt.strengths = summary["strengths"]
    attempt.tip = summary["tip"]
    attempt.next_step = summary["next_step"]
    attempt.submitted_at = timezone.now()
    attempt.save()
    return attempt


def _apply_scores(attempt: Attempt, answers) -> None:
    """Set the attempt's skill scores, headline, review reasons and status from its answers."""
    totals = scoring.summarise_scores(answers)
    for skill in (*scoring.SKILLS, "overall", "headline"):
        setattr(attempt, skill, totals[skill])
    attempt.review_reasons = scoring.attempt_review_reasons(attempt.overall, answers)
    if attempt.status != Attempt.Status.REVIEWED:
        attempt.status = Attempt.Status.NEEDS_REVIEW if attempt.review_reasons else Attempt.Status.SCORED


# ---------------------------------------------------------------------------
# Admin review and rescoring
# ---------------------------------------------------------------------------
def review_attempt(
    attempt: Attempt,
    reviewer,
    *,
    fluency=None,
    pronunciation=None,
    grammar=None,
    strengths=None,
    tip=None,
    next_step=None,
    reviewer_note=None,
    notify_student=True,
) -> tuple[Attempt, bool]:
    """Save an admin's review (optional score changes and feedback). Returns (attempt, email_sent)."""
    if attempt.status == Attempt.Status.IN_PROGRESS:
        raise ServiceError("This attempt hasn't been submitted yet.", status_code=409)

    for skill, value in (("fluency", fluency), ("pronunciation", pronunciation), ("grammar", grammar)):
        if value is not None:
            setattr(attempt, skill, clamp_score(value))
    attempt.overall = scoring.overall_score(attempt.fluency, attempt.pronunciation, attempt.grammar)
    attempt.headline = scoring.headline_for(attempt.overall)

    if strengths is not None:
        attempt.strengths = [text.strip() for text in strengths if text.strip()][:2]
    # None = not sent (unchanged); an empty text clears the field.
    if tip is not None:
        attempt.tip = tip.strip()
    if next_step is not None:
        attempt.next_step = next_step.strip()
    if reviewer_note is not None:
        attempt.reviewer_note = reviewer_note.strip()

    attempt.status = Attempt.Status.REVIEWED
    attempt.reviewer = reviewer
    attempt.reviewed_at = timezone.now()
    attempt.save()

    email_sent = False
    if notify_student:
        try:
            email_service.send_review_published(attempt)
            email_sent = True
        except email_service.EmailDeliveryError:
            logger.exception("Review email failed for attempt %s", attempt.pk)
    return attempt, email_sent


def rescore_answer(answer: Answer) -> Answer:
    """Run the scoring again on a saved recording (for example after a service outage)."""
    if not answer.audio or not answer.audio.storage.exists(answer.audio.name):
        raise ServiceError("The recording for this answer is missing, so it can't be scored again.", status_code=409)
    with answer.audio.open("rb") as audio:
        result = scoring.evaluate_answer(
            audio,
            question_text=answer.question_text,
            level=answer.attempt.student.level,
            recorded_seconds=answer.duration_seconds,
            filename=f"answer{audio_extension(answer.audio)}",
        )
    recorded_length = answer.duration_seconds
    for field, value in result.as_model_fields().items():
        setattr(answer, field, value)
    if recorded_length:
        answer.duration_seconds = recorded_length
    answer.save()

    attempt = answer.attempt
    if attempt.status in (Attempt.Status.SCORED, Attempt.Status.NEEDS_REVIEW):
        _apply_scores(attempt, list(attempt.answers.all()))
        attempt.save()
    return answer


def _delete_file(storage, name: str) -> None:
    try:
        storage.delete(name)
    except Exception:  # noqa: BLE001 - a leftover file must never break the request
        logger.warning("Could not delete old recording %s", name)


# ---------------------------------------------------------------------------
# Student numbers
# ---------------------------------------------------------------------------
def student_stats(student) -> dict:
    finished = Attempt.objects.filter(student=student, status__in=FINISHED_STATUSES)
    totals = finished.aggregate(
        completed=Count("id"),
        average=Avg("overall"),
        best=Max("overall"),
        fluency=Avg("fluency"),
        pronunciation=Avg("pronunciation"),
        grammar=Avg("grammar"),
    )
    skills = {skill: clamp_score(totals[skill]) for skill in scoring.SKILLS}
    scored_skills = {skill: value for skill, value in skills.items() if value is not None}
    recent = finished.select_related("test").order_by("-submitted_at")[:5]

    return {
        "completed_tests": totals["completed"],
        "in_progress": Attempt.objects.filter(student=student, status=Attempt.Status.IN_PROGRESS).count(),
        "average_score": clamp_score(totals["average"]),
        "best_score": totals["best"],
        "skills": skills,
        "strongest_skill": max(scored_skills, key=scored_skills.get) if scored_skills else None,
        "focus_skill": min(scored_skills, key=scored_skills.get) if scored_skills else None,
        "recent": [
            {
                "id": attempt.id,
                "test_title": attempt.test.title,
                "overall": attempt.overall,
                "status": attempt.status,
                "submitted_at": attempt.submitted_at,
            }
            for attempt in recent
        ],
    }


# ---------------------------------------------------------------------------
# Admin dashboard and reports
# ---------------------------------------------------------------------------
def _finished():
    return Attempt.objects.filter(status__in=FINISHED_STATUSES)


def dashboard_stats() -> dict:
    now = timezone.now()
    week_start, previous_start = now - timedelta(days=7), now - timedelta(days=14)
    this_week = _finished().filter(submitted_at__gte=week_start)
    last_week = _finished().filter(submitted_at__gte=previous_start, submitted_at__lt=week_start)
    students = User.objects.filter(role=User.Role.STUDENT)

    this_week_totals = this_week.aggregate(
        count=Count("id"),
        average=Avg("overall"),
        fluency=Avg("fluency"),
        pronunciation=Avg("pronunciation"),
        grammar=Avg("grammar"),
        active=Count("student", distinct=True),
    )
    last_week_totals = last_week.aggregate(count=Count("id"), average=Avg("overall"))
    recent = _finished().select_related("student", "test").order_by("-submitted_at")[:6]

    return {
        "students": {
            "total": students.filter(is_active=True).count(),
            "new_this_week": students.filter(date_joined__gte=week_start).count(),
            "active_this_week": this_week_totals["active"],
        },
        "attempts": {
            "this_week": this_week_totals["count"],
            "last_week": last_week_totals["count"],
            "change_percent": percent_change(this_week_totals["count"], last_week_totals["count"]),
        },
        "average_score": {
            "this_week": clamp_score(this_week_totals["average"]),
            "last_week": clamp_score(last_week_totals["average"]),
        },
        "skills_this_week": {skill: clamp_score(this_week_totals[skill]) for skill in scoring.SKILLS},
        "needs_review": Attempt.objects.filter(status=Attempt.Status.NEEDS_REVIEW).count(),
        "published_tests": MockTest.objects.published().count(),
        "recent_attempts": [
            {
                "id": attempt.id,
                "student_name": attempt.student.full_name,
                "test_title": attempt.test.title,
                "overall": attempt.overall,
                "status": attempt.status,
                "submitted_at": attempt.submitted_at,
            }
            for attempt in recent
        ],
    }


def report_queryset(start, end, *, test_id=None, level=None):
    queryset = _finished().filter(submitted_at__gte=start, submitted_at__lt=end)
    if test_id:
        queryset = queryset.filter(test_id=test_id)
    if level:
        queryset = queryset.filter(student__level=level)
    return queryset


def build_report(start, end, *, test_id=None, level=None) -> dict:
    queryset = report_queryset(start, end, test_id=test_id, level=level)
    totals = queryset.aggregate(
        attempts=Count("id"),
        students=Count("student", distinct=True),
        average=Avg("overall"),
        fluency=Avg("fluency"),
        pronunciation=Avg("pronunciation"),
        grammar=Avg("grammar"),
        reviewed=Count("id", filter=Q(status=Attempt.Status.REVIEWED)),
        needs_review=Count("id", filter=Q(status=Attempt.Status.NEEDS_REVIEW)),
        band_high=Count("id", filter=Q(overall__gte=80)),
        band_mid=Count("id", filter=Q(overall__gte=60, overall__lt=80)),
        band_low=Count("id", filter=Q(overall__lt=60)),
    )
    by_test = (
        queryset.values("test_id", "test__title", "test__level")
        .annotate(
            attempts=Count("id"),
            students=Count("student", distinct=True),
            average=Avg("overall"),
            best=Max("overall"),
            lowest=Min("overall"),
        )
        .order_by("-attempts", "test__title")
    )
    by_level = queryset.values("student__level").annotate(attempts=Count("id"), average=Avg("overall")).order_by("student__level")
    daily = (
        queryset.annotate(day=TruncDate("submitted_at"))
        .values("day")
        .annotate(attempts=Count("id"), average=Avg("overall"))
        .order_by("day")
    )

    return {
        "totals": {
            "attempts": totals["attempts"],
            "students": totals["students"],
            "average_score": clamp_score(totals["average"]),
            "reviewed": totals["reviewed"],
            "needs_review": totals["needs_review"],
        },
        "skills": {skill: clamp_score(totals[skill]) for skill in scoring.SKILLS},
        "score_bands": {"80_and_above": totals["band_high"], "60_to_79": totals["band_mid"], "under_60": totals["band_low"]},
        "by_test": [
            {
                "test_id": row["test_id"],
                "title": row["test__title"],
                "level": row["test__level"],
                "attempts": row["attempts"],
                "students": row["students"],
                "average_score": clamp_score(row["average"]),
                "best_score": row["best"],
                "lowest_score": row["lowest"],
            }
            for row in by_test
        ],
        "by_level": [
            {"level": row["student__level"], "attempts": row["attempts"], "average_score": clamp_score(row["average"])}
            for row in by_level
        ],
        "daily": [
            {"date": row["day"], "attempts": row["attempts"], "average_score": clamp_score(row["average"])}
            for row in daily
        ],
    }


# ---------------------------------------------------------------------------
# n8n automations
# ---------------------------------------------------------------------------
def pending_review_alerts(limit: int = 50) -> list[dict]:
    """Attempts that need review and haven't been emailed to admins yet."""
    attempts = (
        Attempt.objects.filter(status=Attempt.Status.NEEDS_REVIEW, alerted_at__isnull=True)
        .select_related("student", "test")
        .order_by("submitted_at")[:limit]
    )
    return [
        {
            "id": attempt.id,
            "student_name": attempt.student.full_name,
            "student_email": attempt.student.email,
            "test_title": attempt.test.title,
            "overall": attempt.overall,
            "review_reasons": attempt.review_reasons,
            "submitted_at": attempt.submitted_at,
            "review_url": frontend_url(f"/admin/reviews/{attempt.id}"),
        }
        for attempt in attempts
    ]


def mark_alerted(ids) -> int:
    return Attempt.objects.filter(
        pk__in=ids, status=Attempt.Status.NEEDS_REVIEW, alerted_at__isnull=True
    ).update(alerted_at=timezone.now())


def weekly_summary() -> dict:
    now = timezone.now()
    start = now - timedelta(days=7)
    this_week = report_queryset(start, now)
    last_week = report_queryset(start - timedelta(days=7), start)
    report = build_report(start, now)
    last_totals = last_week.aggregate(count=Count("id"), average=Avg("overall"))

    return {
        "period": {"start": timezone.localdate(start), "end": timezone.localdate(now)},
        "attempts": report["totals"]["attempts"],
        "attempts_last_week": last_totals["count"],
        "change_percent": percent_change(report["totals"]["attempts"], last_totals["count"]),
        "active_students": this_week.values("student").distinct().count(),
        "new_students": User.objects.filter(role=User.Role.STUDENT, date_joined__gte=start).count(),
        "average_score": report["totals"]["average_score"],
        "average_score_last_week": clamp_score(last_totals["average"]),
        "skills": report["skills"],
        "needs_review": Attempt.objects.filter(status=Attempt.Status.NEEDS_REVIEW).count(),
        "top_tests": report["by_test"][:3],
        "dashboard_url": frontend_url("/admin"),
        "reports_url": frontend_url("/admin/reports"),
    }
