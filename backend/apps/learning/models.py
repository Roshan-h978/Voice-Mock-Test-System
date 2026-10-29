"""Quick practice answers and the Mistakes notebook's "learned" marks."""

import secrets
from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


def practice_upload_path(instance, filename: str) -> str:
    """recordings/practice/2026/10/student-7/1a2b3c4d.webm"""
    extension = Path(filename).suffix.lower() or ".webm"
    now = timezone.now()
    return f"recordings/practice/{now:%Y/%m}/student-{instance.student_id}/{secrets.token_hex(6)}{extension}"


class PracticeAnswer(models.Model):
    """One Quick practice answer: a single question, scored straight away. Not part of any test result."""

    class Source(models.TextChoices):
        TESTS = "tests", "From the tests"
        AI = "ai", "AI-written"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="practice_answers")
    topic = models.CharField(max_length=40, blank=True)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.AI)
    question_text = models.TextField()
    hint = models.CharField(max_length=255, blank=True)
    time_limit = models.PositiveSmallIntegerField(default=60)
    audio = models.FileField(upload_to=practice_upload_path, max_length=255)
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
    score_notes = models.JSONField(default=list, blank=True)
    is_demo = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.student} - practice: {self.question_text[:50]}"


class NotebookMark(models.Model):
    """A correction or tip the student ticked as learned. `key` identifies the item (see learning.notebook)."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notebook_marks")
    key = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "key"], name="unique_notebook_mark")]

    def __str__(self):
        return f"{self.student} learned {self.key}"
