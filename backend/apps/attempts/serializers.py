"""Serializers for attempts and answers (student and admin views)."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.tests_manager.models import MockTest

from .models import Answer, Attempt

User = get_user_model()


class AnswerSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = (
            "id",
            "question",
            "question_order",
            "question_text",
            "audio_url",
            "duration_seconds",
            "transcript",
            "word_count",
            "words_per_minute",
            "filler_count",
            "long_pauses",
            "clarity",
            "fluency",
            "pronunciation",
            "grammar",
            "coherence",
            "relevance",
            "overall",
            "strengths",
            "tip",
            "corrections",
            "needs_review",
            "review_reasons",
            "score_notes",
            "is_demo",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_audio_url(self, obj):
        if not obj.audio:
            return None
        url = obj.audio.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and url.startswith("/") else url


class AnswerUploadSerializer(serializers.Serializer):
    question = serializers.IntegerField(min_value=1)
    audio = serializers.FileField(allow_empty_file=True)  # emptiness is reported with a friendlier message
    duration_seconds = serializers.FloatField(required=False, min_value=0, max_value=900)


class StartAttemptSerializer(serializers.Serializer):
    test = serializers.PrimaryKeyRelatedField(queryset=MockTest.objects.all())


class AttemptTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MockTest
        fields = ("id", "title", "level", "prep_seconds", "answer_seconds", "allow_retake")


class StudentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name", "email", "level")


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------
class AttemptListSerializer(serializers.ModelSerializer):
    test = AttemptTestSerializer(read_only=True)
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    answer_count = serializers.SerializerMethodField()

    class Meta:
        model = Attempt
        fields = (
            "id",
            "test",
            "status",
            "status_label",
            "fluency",
            "pronunciation",
            "grammar",
            "overall",
            "headline",
            "started_at",
            "submitted_at",
            "reviewed_at",
            "answer_count",
        )

    def get_answer_count(self, obj):
        count = getattr(obj, "answer_count", None)
        return obj.answers.count() if count is None else count


class AttemptDetailSerializer(AttemptListSerializer):
    """The Speaking test and Results pages: questions, answers and feedback."""

    questions = serializers.SerializerMethodField()
    answers = AnswerSerializer(many=True, read_only=True)
    reviewer_name = serializers.SerializerMethodField()

    class Meta(AttemptListSerializer.Meta):
        fields = AttemptListSerializer.Meta.fields + (
            "summary",
            "strengths",
            "tip",
            "next_step",
            "review_reasons",
            "reviewer_name",
            "reviewer_note",
            "questions",
            "answers",
        )

    def get_questions(self, obj):
        answered = {answer.question_id for answer in obj.answers.all()}
        return [
            {
                "id": question.id,
                "order": question.order,
                "text": question.text,
                "hint": question.hint,
                "time_limit": question.time_limit,
                "answered": question.id in answered,
            }
            for question in obj.test.questions.all()
        ]

    def get_reviewer_name(self, obj):
        return obj.reviewer.full_name if obj.reviewer else None


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------
class AdminAttemptListSerializer(AttemptListSerializer):
    student = StudentBriefSerializer(read_only=True)

    class Meta(AttemptListSerializer.Meta):
        fields = AttemptListSerializer.Meta.fields + ("student", "review_reasons", "alerted_at")


class AdminAttemptDetailSerializer(AttemptDetailSerializer):
    student = StudentBriefSerializer(read_only=True)

    class Meta(AttemptDetailSerializer.Meta):
        fields = AttemptDetailSerializer.Meta.fields + ("student",)


class ReviewSerializer(serializers.Serializer):
    """An admin's review. Every field is optional; send only what changes."""

    fluency = serializers.IntegerField(required=False, min_value=0, max_value=100)
    pronunciation = serializers.IntegerField(required=False, min_value=0, max_value=100)
    grammar = serializers.IntegerField(required=False, min_value=0, max_value=100)
    strengths = serializers.ListField(
        child=serializers.CharField(max_length=300), required=False, max_length=2
    )
    tip = serializers.CharField(required=False, allow_blank=True, max_length=500)
    next_step = serializers.CharField(required=False, allow_blank=True, max_length=500)
    reviewer_note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    notify_student = serializers.BooleanField(required=False, default=True)
