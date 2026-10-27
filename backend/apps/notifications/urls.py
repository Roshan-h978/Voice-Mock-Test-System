"""Notification URLs, mounted at /api/notifications/."""

from django.urls import path

from . import views

urlpatterns = [
    path("pending-reviews/", views.PendingReviewsView.as_view(), name="notifications-pending-reviews"),
    path("pending-reviews/mark-alerted/", views.MarkAlertedView.as_view(), name="notifications-mark-alerted"),
    path("weekly-summary/", views.WeeklySummaryView.as_view(), name="notifications-weekly-summary"),
    path("test-email/", views.TestEmailView.as_view(), name="notifications-test-email"),
]
