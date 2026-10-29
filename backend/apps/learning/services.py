"""
Quick practice, the Mistakes notebook and My progress: the logic behind the student's learning pages.
"""

import hashlib
import logging
import random
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone

from apps.attempts.models import FINISHED_STATUSES, Answer, Attempt
from apps.attempts.services import _delete_file
from apps.common.utils import ServiceError, audio_extension, clamp_score, validate_audio_upload
from apps.evaluation import question_writer, scoring
from apps.tests_manager.models import MockTest, Question

from .models import NotebookMark, PracticeAnswer

logger = logging.getLogger(__name__)

SKILL_ADVICE = {
    "fluency": "Speak for the whole time without long stops. Use short linking phrases such as “for example” or “the main reason is” instead of “um”.",
    "pronunciation": "Record yourself reading a short text, listen back, and repeat the words that sounded unclear. Speak a little slower and finish each word.",
    "grammar": "Choose one tense you use often (for example the past simple) and practise five sentences with it every day. Check the corrections in your notebook.",
}


# ---------------------------------------------------------------------------
# Quick practice
# ---------------------------------------------------------------------------
def practice_question(student, *, source: str, topic: str = "") -> dict:
    """A question to practise: from the published tests, or freshly written by the AI for the chosen topic."""
    recent = list(
        PracticeAnswer.objects.filter(student=student).order_by("-created_at").values_list("question_text", flat=True)[:30]
    )
    if source == PracticeAnswer.Source.TESTS:
        questions = list(
            Question.objects.filter(test__status=MockTest.Status.PUBLISHED)
            .exclude(text__in=recent)
            .select_related("test")[:300]
        ) or list(Question.objects.filter(test__status=MockTest.Status.PUBLISHED).select_related("test")[:300])
        if not questions:
            raise ServiceError("There are no published test questions yet. Try an AI question instead.", status_code=404)
        question = random.choice(questions)
        return {
            "source": source,
            "topic": "",
            "topic_label": question.test.title,
            "question_text": question.text,
            "hint": question.hint,
            "time_limit": question.time_limit,
            "is_demo": False,
        }

    topic_label = question_writer.TOPICS.get(topic, "")
    questions, is_demo = question_writer.write_questions(
        count=1, level=student.level, topic=topic_label or "everyday life", existing=recent, answer_seconds=60
    )
    return {
        "source": PracticeAnswer.Source.AI,
        "topic": topic if topic_label else "",
        "topic_label": topic_label or "Everyday life",
        "question_text": questions[0]["text"],
        "hint": questions[0]["hint"],
        "time_limit": 60,
        "is_demo": is_demo,
    }


def save_practice_answer(student, *, audio, question_text, hint="", topic="", source="ai", time_limit=60, recorded_seconds=None):
    """Score one practice recording straight away and keep it in the student's practice history."""
    error = validate_audio_upload(audio)
    if error:
        raise ServiceError(error)
    extension = audio_extension(audio)
    result = scoring.evaluate_answer(
        audio,
        question_text=question_text,
        level=student.level,
        time_limit=time_limit,
        recorded_seconds=recorded_seconds,
        filename=f"answer{extension}",
        content_type=(audio.content_type or "audio/webm").split(";")[0],
    )
    fields = {name: value for name, value in result.as_model_fields().items() if name in PRACTICE_FIELDS}
    answer = PracticeAnswer(
        student=student,
        question_text=question_text,
        hint=hint,
        topic=topic,
        source=source,
        time_limit=time_limit,
        **fields,
    )
    if recorded_seconds:
        answer.duration_seconds = round(float(recorded_seconds), 1)
    audio.seek(0)
    answer.audio.save(f"practice{extension}", audio, save=False)
    answer.save()
    return answer


PRACTICE_FIELDS = {field.name for field in PracticeAnswer._meta.get_fields()}


def delete_practice_answer(answer: PracticeAnswer) -> None:
    name, storage = answer.audio.name, answer.audio.storage
    with transaction.atomic():
        answer.delete()
        if name:
            transaction.on_commit(lambda: _delete_file(storage, name))


# ---------------------------------------------------------------------------
# Mistakes notebook
# ---------------------------------------------------------------------------
def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9']+", " ", (text or "").lower()).strip()


def item_key(kind: str, *parts: str) -> str:
    """Stable id for a correction ("c") or tip ("t"): the same mistake made twice is one notebook item."""
    raw = kind + "|" + "|".join(_norm(part) for part in parts)
    return hashlib.sha1(raw.encode()).hexdigest()


def notebook(student, show: str = "to_learn") -> dict:
    """Corrections and tips from finished tests and practice, grouped, newest first, with learned marks."""
    learned = set(NotebookMark.objects.filter(student=student).values_list("key", flat=True))
    sources = []
    test_answers = (
        Answer.objects.filter(attempt__student=student, attempt__status__in=FINISHED_STATUSES)
        .select_related("attempt__test")
        .order_by("-created_at")[:500]
    )
    for answer in test_answers:
        sources.append(
            (
                answer.created_at,
                answer.corrections,
                answer.tip,
                {
                    "kind": "test",
                    "title": answer.attempt.test.title,
                    "question": answer.question_text,
                    "link": f"/student/results/{answer.attempt_id}",
                },
            )
        )
    for practice in PracticeAnswer.objects.filter(student=student).order_by("-created_at")[:500]:
        sources.append(
            (
                practice.created_at,
                practice.corrections,
                practice.tip,
                {"kind": "practice", "title": "Quick practice", "question": practice.question_text, "link": f"/student/practice/{practice.pk}"},
            )
        )
    sources.sort(key=lambda item: item[0], reverse=True)

    corrections, tips = {}, {}
    for when, items, tip, origin in sources:
        for item in items or []:
            said, better = (item.get("said") or "").strip(), (item.get("better") or "").strip()
            if not said or not better or _norm(said) == _norm(better):
                continue
            _collect(corrections, item_key("c", said, better), when, origin, said=said, better=better)
        if tip and tip.strip():
            _collect(tips, item_key("t", tip), when, origin, text=tip.strip())

    def finish(groups):
        rows = []
        for key, row in groups.items():
            row["key"] = key
            row["learned"] = key in learned
            rows.append(row)
        rows.sort(key=lambda row: (-row["count"], -row["last_seen"].timestamp()))
        return rows

    all_corrections, all_tips = finish(corrections), finish(tips)
    totals = {
        "corrections": len(all_corrections),
        "tips": len(all_tips),
        "learned": sum(row["learned"] for row in all_corrections + all_tips),
    }
    if show == "learned":
        all_corrections = [row for row in all_corrections if row["learned"]]
        all_tips = [row for row in all_tips if row["learned"]]
    elif show != "all":
        all_corrections = [row for row in all_corrections if not row["learned"]]
        all_tips = [row for row in all_tips if not row["learned"]]
    return {"corrections": all_corrections, "tips": all_tips, "totals": totals}


def _collect(groups: dict, key: str, when, origin: dict, **fields) -> None:
    row = groups.get(key)
    if row is None:
        groups[key] = {**fields, "count": 1, "last_seen": when, "sources": [origin]}
        return
    row["count"] += 1
    # Each test (or Quick practice) is listed once, with its latest link.
    seen = {(source["kind"], source["title"]) for source in row["sources"]}
    if len(row["sources"]) < 3 and (origin["kind"], origin["title"]) not in seen:
        row["sources"].append(origin)


def set_learned(student, key: str, learned: bool) -> None:
    if learned:
        NotebookMark.objects.get_or_create(student=student, key=key)
    else:
        NotebookMark.objects.filter(student=student, key=key).delete()


# ---------------------------------------------------------------------------
# My progress
# ---------------------------------------------------------------------------
def progress(student, days: int = 90) -> dict:
    now = timezone.now()
    today = timezone.localdate()
    since = now - timedelta(days=days) if days else None

    finished = Attempt.objects.filter(student=student, status__in=FINISHED_STATUSES, submitted_at__isnull=False).select_related("test")
    practice = PracticeAnswer.objects.filter(student=student)

    in_range = finished.filter(submitted_at__gte=since) if since else finished
    timeline = [
        {
            "id": attempt.id,
            "kind": "test",
            "title": attempt.test.title,
            "date": attempt.submitted_at,
            "overall": attempt.overall,
            "fluency": attempt.fluency,
            "pronunciation": attempt.pronunciation,
            "grammar": attempt.grammar,
        }
        for attempt in in_range.order_by("submitted_at")
    ]
    practice_in_range = practice.filter(created_at__gte=since) if since else practice
    practice_points = [
        {
            "id": item.id,
            "kind": "practice",
            "title": "Quick practice",
            "date": item.created_at,
            "overall": item.overall,
            "fluency": item.fluency,
            "pronunciation": item.pronunciation,
            "grammar": item.grammar,
        }
        for item in practice_in_range.order_by("created_at")
    ]

    # Skill trend: the last 5 scored items (tests and practice) against the 5 before them.
    events = sorted(
        [*(dict(point) for point in _all_points(finished)), *(dict(point) for point in _all_points(practice, practice=True))],
        key=lambda point: point["date"],
    )
    recent, before = events[-5:], events[-10:-5]
    skills = {}
    for skill in (*scoring.SKILLS, "overall"):
        current = _mean(point[skill] for point in recent)
        previous = _mean(point[skill] for point in before)
        skills[skill] = {
            "current": current,
            "previous": previous,
            "change": None if current is None or previous is None else current - previous,
        }
    scored = {skill: skills[skill]["current"] for skill in scoring.SKILLS if skills[skill]["current"] is not None}
    focus = min(scored, key=scored.get) if scored else None

    best_by_test = [
        {
            "test_id": row["test_id"],
            "title": row["test__title"],
            "attempts": row["attempts"],
            "best": row["best"],
            "last_taken": row["last_taken"],
        }
        for row in finished.values("test_id", "test__title")
        .annotate(attempts=Count("id"), best=Max("overall"), last_taken=Max("submitted_at"))
        .order_by("-last_taken")
    ]

    # Activity per day (local dates) for the last 12 weeks, and practice streaks over all time.
    day_counts = {}
    for stamp in [*finished.values_list("submitted_at", flat=True), *practice.values_list("created_at", flat=True)]:
        day = timezone.localdate(stamp)
        day_counts[day] = day_counts.get(day, 0) + 1
    start = today - timedelta(days=83)
    activity = [
        {"date": (start + timedelta(days=offset)).isoformat(), "count": day_counts.get(start + timedelta(days=offset), 0)}
        for offset in range(84)
    ]
    current_streak, longest_streak = _streaks(set(day_counts), today)

    seconds = (
        (Answer.objects.filter(attempt__in=finished).aggregate(total=Sum("duration_seconds"))["total"] or 0)
        + (practice.aggregate(total=Sum("duration_seconds"))["total"] or 0)
    )
    return {
        "days": days,
        "totals": {
            "tests_completed": finished.count(),
            "practice_answers": practice.count(),
            "minutes_spoken": int(seconds / 60 + 0.5),  # rounded half up
            "active_days_30": sum(1 for day in day_counts if day > today - timedelta(days=30)),
            "average_score": clamp_score(finished.aggregate(value=Avg("overall"))["value"]),
        },
        "timeline": timeline,
        "practice": practice_points,
        "skills": skills,
        "focus_skill": focus,
        "focus_advice": SKILL_ADVICE.get(focus, ""),
        "best_by_test": best_by_test,
        "activity": activity,
        "streak": {"current": current_streak, "longest": longest_streak},
    }


def _all_points(queryset, practice=False):
    date_field = "created_at" if practice else "submitted_at"
    for row in queryset.order_by(date_field).values(date_field, "overall", "fluency", "pronunciation", "grammar"):
        row["date"] = row.pop(date_field)
        yield row


def _mean(values):
    values = [value for value in values if value is not None]
    return round(sum(values) / len(values)) if values else None


def _streaks(days: set, today) -> tuple[int, int]:
    """Current streak (days in a row up to today, or up to yesterday if nothing yet today) and the longest ever."""
    current = 0
    day = today if today in days else today - timedelta(days=1)
    while day in days:
        current += 1
        day -= timedelta(days=1)
    longest, run, previous = 0, 0, None
    for day in sorted(days):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    return current, longest
