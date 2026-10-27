"""Mock tests and their speaking questions."""

import math

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Count, IntegerField, Max, OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.accounts.models import User


class MockTestQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=MockTest.Status.PUBLISHED)

    def with_question_count(self):
        """Annotate question_count without joining (keeps other aggregates accurate)."""
        counts = (
            Question.objects.filter(test=OuterRef("pk"))
            .order_by()
            .values("test")
            .annotate(total=Count("id"))
            .values("total")
        )
        return self.annotate(question_count=Coalesce(Subquery(counts, output_field=IntegerField()), 0))


class MockTest(models.Model):
    """A speaking test made of one or more questions."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    level = models.CharField(max_length=20, choices=User.Level.choices, default=User.Level.BEGINNER)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    prep_seconds = models.PositiveSmallIntegerField(
        default=15,
        validators=[MaxValueValidator(300)],
        help_text="Thinking time before each answer, in seconds.",
    )
    answer_seconds = models.PositiveSmallIntegerField(
        default=60,
        validators=[MinValueValidator(10), MaxValueValidator(300)],
        help_text="Speaking time for each answer, in seconds.",
    )
    allow_retake = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tests",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MockTestQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "mock test"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def estimated_minutes(self, question_count=None) -> int:
        count = self.questions.count() if question_count is None else question_count
        if not count:
            return 0
        return max(1, math.ceil(count * (self.prep_seconds + self.answer_seconds) / 60))


class Question(models.Model):
    """One speaking prompt inside a mock test."""

    test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField(default=0, help_text="Position in the test. 0 adds it at the end.")
    text = models.TextField()
    hint = models.CharField(max_length=255, blank=True)
    answer_seconds = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(10), MaxValueValidator(300)],
        help_text="Leave empty to use the test's speaking time.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"Q{self.order}: {self.text[:60]}"

    def save(self, *args, **kwargs):
        if not self.order:
            last = Question.objects.filter(test_id=self.test_id).aggregate(last=Max("order"))["last"] or 0
            self.order = last + 1
        super().save(*args, **kwargs)

    @property
    def time_limit(self) -> int:
        return self.answer_seconds or self.test.answer_seconds
