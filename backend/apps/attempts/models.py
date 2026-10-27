"""Test attempts and the recorded answers inside them."""

import secrets
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.tests_manager.models import MockTest, Question


def recording_upload_path(instance, filename: str) -> str:
    """recordings/2026/10/attempt-42/q3-1a2b3c4d.webm"""
    extension = Path(filename).suffix.lower() or ".webm"
    now = timezone.now()
    return (
        f"recordings/{now:%Y/%m}/attempt-{instance.attempt_id}/"
        f"q{instance.question_order}-{secrets.token_hex(4)}{extension}"
    )


class Attempt(models.Model):
    """One student taking one mock test."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SCORED = "scored", "Scored"
        NEEDS_REVIEW = "needs_review", "Needs review"
        REVIEWED = "reviewed", "Reviewed"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    test = models.ForeignKey(MockTest, on_delete=models.PROTECT, related_name="attempts")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True)

    # Skill scores, 0-100 (filled when the attempt is submitted, adjustable by a reviewer)
    fluency = models.PositiveSmallIntegerField(null=True, blank=True)
    pronunciation = models.PositiveSmallIntegerField(null=True, blank=True)
    grammar = models.PositiveSmallIntegerField(null=True, blank=True)
    overall = models.PositiveSmallIntegerField(null=True, blank=True)

    # Feedback shown on the Results page
    headline = models.CharField(max_length=80, blank=True)
    summary = models.TextField(blank=True)
    strengths = models.JSONField(default=list, blank=True)
    tip = models.TextField(blank=True)
    next_step = models.TextField(blank=True)
    review_reasons = models.JSONField(default=list, blank=True)

    # Admin review
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_attempts",
    )
    reviewer_note = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    alerted_at = models.DateTimeField(null=True, blank=True, help_text="When n8n emailed admins about this review.")

    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [models.Index(fields=["status", "alerted_at"])]

    def __str__(self):
        return f"{self.student} - {self.test} ({self.get_status_display()})"

    @property
    def is_finished(self) -> bool:
        return self.status in FINISHED_STATUSES


FINISHED_STATUSES = (Attempt.Status.SCORED, Attempt.Status.NEEDS_REVIEW, Attempt.Status.REVIEWED)


class Answer(models.Model):
    """A recorded answer to one question, with its transcript and scores.

    question_order and question_text are copies, so results stay readable if a question changes later.
    """

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.SET_NULL, null=True, blank=True, related_name="answers")
    question_order = models.PositiveSmallIntegerField()
    question_text = models.TextField()
    audio = models.FileField(upload_to=recording_upload_path, max_length=255)
    duration_seconds = models.FloatField(null=True, blank=True)

    # Speech measurements
    transcript = models.TextField(blank=True)
    word_count = models.PositiveIntegerField(default=0)
    words_per_minute = models.PositiveSmallIntegerField(null=True, blank=True)
    filler_count = models.PositiveSmallIntegerField(default=0)
    long_pauses = models.PositiveSmallIntegerField(default=0)
    clarity = models.PositiveSmallIntegerField(null=True, blank=True)

    # Scores, 0-100
    fluency = models.PositiveSmallIntegerField(null=True, blank=True)
    pronunciation = models.PositiveSmallIntegerField(null=True, blank=True)
    grammar = models.PositiveSmallIntegerField(null=True, blank=True)
    coherence = models.PositiveSmallIntegerField(null=True, blank=True)
    relevance = models.PositiveSmallIntegerField(null=True, blank=True)
    overall = models.PositiveSmallIntegerField(null=True, blank=True)

    # Feedback
    strengths = models.JSONField(default=list, blank=True)
    tip = models.TextField(blank=True)
    corrections = models.JSONField(default=list, blank=True)
    review_reasons = models.JSONField(default=list, blank=True)
    needs_review = models.BooleanField(default=False)
    is_demo = models.BooleanField(default=False, help_text="Scored in demo mode (sample values).")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["question_order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["attempt", "question"], name="unique_answer_per_question"),
        ]

    def __str__(self):
        return f"Attempt {self.attempt_id} - Q{self.question_order}"
