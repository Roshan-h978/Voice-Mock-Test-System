"""Student learning pages: Quick practice, Mistakes notebook and My progress."""

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsStudent
from apps.common.throttles import AIWriteThrottle, PracticeThrottle
from apps.common.utils import StandardPagination
from apps.evaluation.question_writer import TOPICS

from . import services
from .models import PracticeAnswer
from .serializers import (
    NotebookMarkSerializer,
    PracticeAnswerSerializer,
    PracticeQuestionRequestSerializer,
    PracticeUploadSerializer,
)


class PracticeTopicsView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        return Response([{"value": slug, "label": label} for slug, label in TOPICS.items()])


class PracticeQuestionView(APIView):
    """POST {"source": "ai" | "tests", "topic": "travel"}: a question to practise (nothing is saved yet)."""

    permission_classes = [IsStudent]

    def get_throttles(self):
        # Only AI-written questions count against the AI limit.
        if self.request.data.get("source", PracticeAnswer.Source.AI) == PracticeAnswer.Source.AI:
            return [AIWriteThrottle()]
        return super().get_throttles()

    def post(self, request):
        serializer = PracticeQuestionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(services.practice_question(request.user, **serializer.validated_data))


class PracticeAnswerListCreateView(generics.ListCreateAPIView):
    """GET: my practice history. POST (multipart): audio + question_text (+ hint, topic, source, time_limit) -> scored answer."""

    permission_classes = [IsStudent]
    serializer_class = PracticeAnswerSerializer
    pagination_class = StandardPagination
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return PracticeAnswer.objects.filter(student=self.request.user)

    def get_throttles(self):
        return [PracticeThrottle()] if self.request.method == "POST" else super().get_throttles()

    def create(self, request, *args, **kwargs):
        serializer = PracticeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        answer = services.save_practice_answer(
            request.user,
            audio=data["audio"],
            question_text=data["question_text"],
            hint=data.get("hint", ""),
            topic=data.get("topic", ""),
            source=data["source"],
            time_limit=data["time_limit"],
            recorded_seconds=data.get("duration_seconds"),
        )
        return Response(PracticeAnswerSerializer(answer, context={"request": request}).data, status=status.HTTP_201_CREATED)


class PracticeAnswerDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsStudent]
    serializer_class = PracticeAnswerSerializer

    def get_queryset(self):
        return PracticeAnswer.objects.filter(student=self.request.user)

    def perform_destroy(self, instance):
        services.delete_practice_answer(instance)


class NotebookView(APIView):
    """?show=to_learn (default) | learned | all"""

    permission_classes = [IsStudent]

    def get(self, request):
        return Response(services.notebook(request.user, request.query_params.get("show", "to_learn")))


class NotebookMarkView(APIView):
    """POST {"key": "...", "learned": true|false}"""

    permission_classes = [IsStudent]

    def post(self, request):
        serializer = NotebookMarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.set_learned(request.user, serializer.validated_data["key"], serializer.validated_data["learned"])
        return Response(serializer.validated_data)


class ProgressView(APIView):
    """?days=30 | 90 (default) | 365 | 0 (all time)"""

    permission_classes = [IsStudent]

    def get(self, request):
        days = request.query_params.get("days", "90")
        days = int(days) if days.isdigit() and int(days) in (0, 30, 90, 365) else 90
        return Response(services.progress(request.user, days))


