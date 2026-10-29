"""Notification URLs, mounted at /api/notifications/."""

from django.urls import path

from . import views

urlpatterns = [
    # In-app notifications for the signed-in person
    path("", views.MyNotificationListView.as_view(), name="notifications"),
    path("unread-count/", views.UnreadCountView.as_view(), name="notifications-unread-count"),
    path("<int:pk>/read/", views.MarkReadView.as_view(), name="notifications-read"),
    path("read-all/", views.MarkAllReadView.as_view(), name="notifications-read-all"),
    # n8n automations and the admin's test email
    path("pending-reviews/", views.PendingReviewsView.as_view(), name="notifications-pending-reviews"),
    path("pending-reviews/mark-alerted/", views.MarkAlertedView.as_view(), name="notifications-mark-alerted"),
    path("weekly-summary/", views.WeeklySummaryView.as_view(), name="notifications-weekly-summary"),
    path("test-email/", views.TestEmailView.as_view(), name="notifications-test-email"),
]
