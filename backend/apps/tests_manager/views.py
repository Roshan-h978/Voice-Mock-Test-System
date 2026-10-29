"""Mock test endpoints: published tests for students, full management for admins."""

from django.db import transaction
from django.db.models import Avg, Count, Max, Q
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.attempts.models import FINISHED_STATUSES
from apps.attempts.services import delete_attempts
from apps.common.throttles import AdminAIWriteThrottle
from apps.common.utils import ServiceError
from apps.evaluation import question_writer
from apps.notifications import inbox

from .models import MockTest, Question
from .serializers import (
    ARCHIVED_QUESTIONS_MESSAGE,
    AdminQuestionSerializer,
    AiCreateTestSerializer,
    AiWriteSerializer,
    BulkQuestionsSerializer,
    GenerateQuestionsSerializer,
    AdminTestSerializer,
    TestDetailSerializer,
    TestSummarySerializer,
)


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------
def tests_for_student(user):
    """Tests with question counts and this student's own attempt numbers."""
    mine = Q(attempts__student=user, attempts__status__in=FINISHED_STATUSES)
    queryset = MockTest.objects.with_question_count().annotate(
        my_attempt_count=Count("attempts", filter=mine),
        my_best_score=Max("attempts__overall", filter=mine),
    )
    return queryset if user.is_admin else queryset.published()


class StudentTestListView(generics.ListAPIView):
    """Published tests. Optional filter: ?level=beginner|intermediate|advanced"""

    serializer_class = TestSummarySerializer
    pagination_class = None

    def get_queryset(self):
        queryset = tests_for_student(self.request.user).filter(status=MockTest.Status.PUBLISHED)
        level = self.request.query_params.get("level")
        if level:
            queryset = queryset.filter(level=level)
        return queryset.order_by("-published_at", "title")


class StudentTestDetailView(generics.RetrieveAPIView):
    """One test with its questions. Admins can preview drafts."""

    serializer_class = TestDetailSerializer

    def get_queryset(self):
        return tests_for_student(self.request.user).prefetch_related("questions")


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------
class AdminTestViewSet(viewsets.ModelViewSet):
    """Create, edit, publish, archive and delete tests. Filters: ?status= ?level= ?search="""

    permission_classes = [IsAdmin]
    serializer_class = AdminTestSerializer
    pagination_class = None

    def get_queryset(self):
        finished = Q(attempts__status__in=FINISHED_STATUSES)
        queryset = (
            MockTest.objects.select_related("created_by")
            .with_question_count()
            .annotate(
                attempt_count=Count("attempts", filter=finished),
                average_score=Avg("attempts__overall", filter=finished),
            )
        )
        params = self.request.query_params
        if params.get("status") in MockTest.Status.values:
            queryset = queryset.filter(status=params["status"])
        if params.get("level"):
            queryset = queryset.filter(level=params["level"])
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        first_publish = serializer.instance.published_at is None
        test = serializer.save()
        if first_publish and test.status == MockTest.Status.PUBLISHED:
            inbox.test_published(test)

    def destroy(self, request, *args, **kwargs):
        """A test that students have taken is deleted only with ?with_results=true (its results go too)."""
        test = self.get_object()
        with_results = request.query_params.get("with_results", "").lower() in ("1", "true", "yes")
        if test.attempts.exists() and not with_results:
            raise ServiceError(
                "Students have taken this test. Archive it to keep their results, or delete it together with its results.",
                status_code=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            delete_attempts(test.attempts.all())
            test.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminQuestionViewSet(viewsets.ModelViewSet):
    """Questions of a test. List with ?test=<id>; reorder with POST /reorder/."""

    permission_classes = [IsAdmin]
    serializer_class = AdminQuestionSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Question.objects.select_related("test")
        if self.action == "list":
            test_id = self.request.query_params.get("test", "")
            if not test_id.isdigit():
                raise ValidationError({"test": "Add ?test=<test id> to list its questions."})
            queryset = queryset.filter(test_id=test_id)
        return queryset.order_by("order", "id")

    def perform_destroy(self, instance):
        test = instance.test
        if test.status == MockTest.Status.ARCHIVED:
            raise ServiceError(ARCHIVED_QUESTIONS_MESSAGE)
        if test.status == MockTest.Status.PUBLISHED and test.questions.count() <= 1:
            raise ServiceError("A published test needs at least one question. Move it back to draft first.")
        with transaction.atomic():
            instance.delete()
            renumber_questions(test)

    @action(detail=False, methods=["post"], throttle_classes=[AdminAIWriteThrottle])
    def generate(self, request):
        """Body: {"test": 3, "count": 3, "topic": "optional"}. Returns suggestions only; nothing is saved."""
        serializer = GenerateQuestionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.validated_data["test"]
        questions, is_demo = question_writer.write_questions(
            count=serializer.validated_data["count"],
            level=test.level,
            topic=serializer.validated_data.get("topic", ""),
            title=test.title,
            description=test.description,
            existing=list(test.questions.values_list("text", flat=True)),
            answer_seconds=test.answer_seconds,
        )
        return Response({"questions": questions, "is_demo": is_demo})

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        """Body: {"test": 3, "questions": [{"text": "...", "hint": "...", "answer_seconds": null}]}. Adds them all at the end."""
        serializer = BulkQuestionsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.validated_data["test"]
        with transaction.atomic():
            for item in serializer.validated_data["questions"]:
                Question.objects.create(test=test, **item)
        questions = Question.objects.filter(test=test).select_related("test").order_by("order", "id")
        return Response(AdminQuestionSerializer(questions, many=True).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        """Body: {"test": 3, "order": [12, 10, 11]} — question ids in their new order."""
        test_id = request.data.get("test")
        ordered_ids = request.data.get("order")
        if not isinstance(ordered_ids, list) or not all(isinstance(item, int) for item in ordered_ids):
            raise ValidationError({"order": "Send the question ids as a list, in the new order."})
        if MockTest.objects.filter(pk=test_id, status=MockTest.Status.ARCHIVED).exists():
            raise ServiceError(ARCHIVED_QUESTIONS_MESSAGE)
        current_ids = set(Question.objects.filter(test_id=test_id).values_list("id", flat=True))
        if not current_ids or set(ordered_ids) != current_ids or len(ordered_ids) != len(current_ids):
            raise ValidationError({"order": "The list must contain every question of this test exactly once."})
        with transaction.atomic():
            for position, question_id in enumerate(ordered_ids, start=1):
                Question.objects.filter(pk=question_id).update(order=position)
        questions = Question.objects.filter(test_id=test_id).select_related("test").order_by("order")
        return Response(AdminQuestionSerializer(questions, many=True).data)


def renumber_questions(test) -> None:
    """Close gaps in question numbers after a delete: 1, 2, 3, ..."""
    for position, question in enumerate(test.questions.order_by("order", "id"), start=1):
        if question.order != position:
            Question.objects.filter(pk=question.pk).update(order=position)


# ---------------------------------------------------------------------------
# AI generator page (admins)
# ---------------------------------------------------------------------------
class AdminAiWriteView(APIView):
    """POST {topic, level, count, answer_seconds, style, with_title, test?, exclude?}.

    Returns {"questions": [...], "is_demo"} plus "title" and "description" when with_title is true.
    Nothing is saved. `test` and `exclude` keep the AI from repeating questions.
    """

    permission_classes = [IsAdmin]
    throttle_classes = [AdminAIWriteThrottle]

    def post(self, request):
        serializer = AiWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        existing = list(data["exclude"])
        if data["test"] is not None:
            existing += list(data["test"].questions.values_list("text", flat=True))
        options = {
            "topic": data["topic"],
            "count": data["count"],
            "level": data["level"],
            "answer_seconds": data["answer_seconds"],
            "style": data["style"],
            "existing": existing,
        }
        if data["with_title"]:
            return Response(question_writer.write_test(**options))
        questions, is_demo = question_writer.write_questions(**options)
        return Response({"questions": questions, "is_demo": is_demo})


class AdminAiCreateTestView(APIView):
    """POST {title, description, level, prep_seconds, answer_seconds, allow_retake, questions: [...]}: a new draft test."""

    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AiCreateTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        questions = data.pop("questions")
        with transaction.atomic():
            test = MockTest.objects.create(created_by=request.user, status=MockTest.Status.DRAFT, **data)
            for item in questions:
                Question.objects.create(test=test, **item)
        test = MockTest.objects.with_question_count().select_related("created_by").get(pk=test.pk)
        return Response(AdminTestSerializer(test).data, status=status.HTTP_201_CREATED)
