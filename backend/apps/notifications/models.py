"""In-app notifications: the bell in the top bar and the Notifications page."""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """One message for one person. `link` is a page in the app, such as /student/results/12."""

    class Kind(models.TextChoices):
        REVIEW_PUBLISHED = "review_published", "Teacher review"
        TEST_PUBLISHED = "test_published", "New test"
        REVIEW_NEEDED = "review_needed", "Needs review"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    kind = models.CharField(max_length=30, choices=Kind.choices)
    title = models.CharField(max_length=160)
    body = models.CharField(max_length=300, blank=True)
    link = models.CharField(max_length=255, blank=True)
    # Deleting the result or test also removes notifications that point to it.
    attempt = models.ForeignKey("attempts.Attempt", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    test = models.ForeignKey("tests_manager.MockTest", on_delete=models.CASCADE, null=True, blank=True, related_name="+")
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "read_at"])]

    def __str__(self):
        return f"{self.user} - {self.title}"
