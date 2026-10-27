"""Attempt URLs, mounted at /api/."""

from django.urls import path

from . import views

urlpatterns = [
    # Student
    path("attempts/", views.MyAttemptListCreateView.as_view(), name="attempt-list"),
    path("attempts/<int:pk>/", views.MyAttemptDetailView.as_view(), name="attempt-detail"),
    path("attempts/<int:pk>/answers/", views.AnswerUploadView.as_view(), name="attempt-answer-upload"),
    path("attempts/<int:pk>/submit/", views.SubmitAttemptView.as_view(), name="attempt-submit"),
    path("me/stats/", views.MyStatsView.as_view(), name="my-stats"),
    # Admin
    path("admin/attempts/", views.AdminAttemptListView.as_view(), name="admin-attempts"),
    path("admin/attempts/<int:pk>/", views.AdminAttemptDetailView.as_view(), name="admin-attempt-detail"),
    path("admin/attempts/<int:pk>/review/", views.AdminReviewView.as_view(), name="admin-attempt-review"),
    path("admin/dashboard/", views.AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/reports/", views.AdminReportView.as_view(), name="admin-reports"),
    path("admin/reports/export/", views.AdminReportExportView.as_view(), name="admin-reports-export"),
]
