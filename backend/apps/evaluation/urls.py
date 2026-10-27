"""Evaluation URLs, mounted at /api/evaluation/."""

from django.urls import path

from . import views

urlpatterns = [
    path("config/", views.EvaluationConfigView.as_view(), name="evaluation-config"),
    path("answers/<int:pk>/rescore/", views.RescoreAnswerView.as_view(), name="evaluation-rescore-answer"),
]
