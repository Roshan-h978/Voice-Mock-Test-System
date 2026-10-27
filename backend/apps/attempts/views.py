"""Attempt endpoints: taking a test (students) and reviewing results (admins)."""

import csv

from django.db.models import Count, F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.common.utils import StandardPagination, parse_date_range
from apps.tests_manager.models import Question

from . import services
from .models import FINISHED_STATUSES, Attempt
from .serializers import (
    AdminAttemptDetailSerializer,
    AdminAttemptListSerializer,
    AnswerSerializer,
    AnswerUploadSerializer,
    AttemptDetailSerializer,
    AttemptListSerializer,
    ReviewSerializer,
    StartAttemptSerializer,
)


def detail_queryset():
    return Attempt.objects.select_related("test", "student", "reviewer").prefetch_related(
        "answers", "test__questions"
    )


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------
class MyAttemptListCreateView(generics.ListCreateAPIView):
    """GET: my attempts (?status=finished|in_progress|...&test=<id>). POST {"test": id}: start or resume."""

    serializer_class = AttemptListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = self.request.query_params
        queryset = (
            Attempt.objects.filter(student=self.request.user)
            .select_related("test")
            .annotate(answer_count=Count("answers"))
        )
        state = params.get("status")
        if state == "finished":
            queryset = queryset.filter(status__in=FINISHED_STATUSES)
        elif state in Attempt.Status.values:
            queryset = queryset.filter(status=state)
        if params.get("test", "").isdigit():
            queryset = queryset.filter(test_id=params["test"])
        return queryset.order_by("-started_at")

    def create(self, request, *args, **kwargs):
        serializer = StartAttemptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt, created = services.start_attempt(request.user, serializer.validated_data["test"])
        data = AttemptDetailSerializer(detail_queryset().get(pk=attempt.pk), context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MyAttemptDetailView(generics.RetrieveAPIView):
    serializer_class = AttemptDetailSerializer

    def get_queryset(self):
        return detail_queryset().filter(student=self.request.user)


class AnswerUploadView(APIView):
    """Multipart upload: question=<id>, audio=<file>, duration_seconds=<optional>."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        attempt = get_object_or_404(Attempt.objects.select_related("test", "student"), pk=pk, student=request.user)
        serializer = AnswerUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = get_object_or_404(Question, pk=serializer.validated_data["question"], test_id=attempt.test_id)
        answer = services.save_answer(
            attempt,
            question,
            serializer.validated_data["audio"],
            serializer.validated_data.get("duration_seconds"),
        )
        return Response(AnswerSerializer(answer, context={"request": request}).data, status=status.HTTP_201_CREATED)


class SubmitAttemptView(APIView):
    def post(self, request, pk):
        attempt = get_object_or_404(detail_queryset(), pk=pk, student=request.user)
        services.submit_attempt(attempt)
        attempt = detail_queryset().get(pk=attempt.pk)
        return Response(AttemptDetailSerializer(attempt, context={"request": request}).data)


class MyStatsView(APIView):
    def get(self, request):
        return Response(services.student_stats(request.user))


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------
class AdminAttemptListView(generics.ListAPIView):
    """Filters: ?status= (default: all finished; "all" includes in progress) ?test= ?student= ?search= ?date_from= ?date_to="""

    permission_classes = [IsAdmin]
    serializer_class = AdminAttemptListSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        params = self.request.query_params
        queryset = Attempt.objects.select_related("test", "student").annotate(answer_count=Count("answers"))

        state = params.get("status", "")
        if state in Attempt.Status.values:
            queryset = queryset.filter(status=state)
        elif state != "all":
            queryset = queryset.filter(status__in=FINISHED_STATUSES)

        if params.get("test", "").isdigit():
            queryset = queryset.filter(test_id=params["test"])
        if params.get("student", "").isdigit():
            queryset = queryset.filter(student_id=params["student"])
        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(student__full_name__icontains=search)
                | Q(student__email__icontains=search)
                | Q(test__title__icontains=search)
            )
        if params.get("date_from") or params.get("date_to"):
            start, end, _, _ = parse_date_range(params)
            queryset = queryset.filter(submitted_at__gte=start, submitted_at__lt=end)

        # The review queue shows the oldest first, everything else the newest first.
        if state == Attempt.Status.NEEDS_REVIEW:
            return queryset.order_by("submitted_at")
        # Unsubmitted attempts last on every database (PostgreSQL would put them first).
        return queryset.order_by(F("submitted_at").desc(nulls_last=True), "-started_at")


class AdminAttemptDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAdmin]
    serializer_class = AdminAttemptDetailSerializer

    def get_queryset(self):
        return detail_queryset()


class AdminReviewView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        attempt = get_object_or_404(detail_queryset(), pk=pk)
        serializer = ReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt, email_sent = services.review_attempt(attempt, request.user, **serializer.validated_data)
        attempt = detail_queryset().get(pk=attempt.pk)
        return Response(
            {
                "attempt": AdminAttemptDetailSerializer(attempt, context={"request": request}).data,
                "email_sent": email_sent,
            }
        )


class AdminDashboardView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response(services.dashboard_stats())


def csv_safe(value):
    """Text that Excel would run as a formula (a name starting with "=", "+", "-" or "@") is written as plain text."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def _report_filters(params):
    test_id = params.get("test") if params.get("test", "").isdigit() else None
    level = params.get("level") or None
    return test_id, level


class AdminReportView(APIView):
    """?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&test=<id>&level=<level> (default: last 30 days)"""

    permission_classes = [IsAdmin]

    def get(self, request):
        start, end, start_date, end_date = parse_date_range(request.query_params)
        test_id, level = _report_filters(request.query_params)
        report = services.build_report(start, end, test_id=test_id, level=level)
        return Response({"date_from": start_date, "date_to": end_date, **report})


class AdminReportExportView(APIView):
    """The same filters as the report, as a CSV download."""

    permission_classes = [IsAdmin]
    COLUMNS = (
        "Attempt ID",
        "Student",
        "Email",
        "Level",
        "Test",
        "Status",
        "Fluency",
        "Pronunciation",
        "Grammar",
        "Overall",
        "Submitted",
        "Reviewed by",
    )

    def get(self, request):
        start, end, start_date, end_date = parse_date_range(request.query_params)
        test_id, level = _report_filters(request.query_params)
        attempts = (
            services.report_queryset(start, end, test_id=test_id, level=level)
            .select_related("student", "test", "reviewer")
            .order_by("submitted_at")
        )

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="voice-mock-test-report-{start_date}-to-{end_date}.csv"'
        response.write("﻿")  # lets Excel open the file as UTF-8
        writer = csv.writer(response)
        writer.writerow(self.COLUMNS)
        for attempt in attempts:
            row = [
                attempt.id,
                attempt.student.full_name,
                attempt.student.email,
                attempt.student.get_level_display(),
                attempt.test.title,
                attempt.get_status_display(),
                attempt.fluency,
                attempt.pronunciation,
                attempt.grammar,
                attempt.overall,
                timezone.localtime(attempt.submitted_at).strftime("%Y-%m-%d %H:%M") if attempt.submitted_at else "",
                attempt.reviewer.full_name if attempt.reviewer else "",
            ]
            writer.writerow([csv_safe(value) for value in row])
        return response
