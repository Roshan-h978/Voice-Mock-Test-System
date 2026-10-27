"""Mock test URLs, mounted at /api/."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

router = SimpleRouter()
router.register("admin/tests", views.AdminTestViewSet, basename="admin-tests")
router.register("admin/questions", views.AdminQuestionViewSet, basename="admin-questions")

urlpatterns = [
    path("tests/", views.StudentTestListView.as_view(), name="test-list"),
    path("tests/<int:pk>/", views.StudentTestDetailView.as_view(), name="test-detail"),
    *router.urls,
]
