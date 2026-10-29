"""Learning URLs, mounted at /api/."""

from django.urls import path

from . import views

urlpatterns = [
    path("practice/topics/", views.PracticeTopicsView.as_view(), name="practice-topics"),
    path("practice/question/", views.PracticeQuestionView.as_view(), name="practice-question"),
    path("practice/answers/", views.PracticeAnswerListCreateView.as_view(), name="practice-answers"),
    path("practice/answers/<int:pk>/", views.PracticeAnswerDetailView.as_view(), name="practice-answer-detail"),
    path("me/notebook/", views.NotebookView.as_view(), name="notebook"),
    path("me/notebook/learned/", views.NotebookMarkView.as_view(), name="notebook-learned"),
    path("me/progress/", views.ProgressView.as_view(), name="progress"),
]
