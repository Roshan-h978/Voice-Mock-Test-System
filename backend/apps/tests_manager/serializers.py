"""Serializers for mock tests and questions (student and admin views)."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.attempts.models import FINISHED_STATUSES, Attempt
from apps.evaluation.question_writer import STYLES

from .models import MockTest, Question


def _question_count(test) -> int:
    count = getattr(test, "question_count", None)
    return test.questions.count() if count is None else count


# ---------------------------------------------------------------------------
# Student views
# ---------------------------------------------------------------------------
class QuestionSerializer(serializers.ModelSerializer):
    time_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = ("id", "order", "text", "hint", "time_limit")


class TestSummarySerializer(serializers.ModelSerializer):
    """A published test card on the student dashboard."""

    question_count = serializers.SerializerMethodField()
    estimated_minutes = serializers.SerializerMethodField()
    my_attempt_count = serializers.SerializerMethodField()
    my_best_score = serializers.SerializerMethodField()

    class Meta:
        model = MockTest
        fields = (
            "id",
            "title",
            "description",
            "level",
            "prep_seconds",
            "answer_seconds",
            "allow_retake",
            "question_count",
            "estimated_minutes",
            "my_attempt_count",
            "my_best_score",
            "published_at",
        )

    def get_question_count(self, obj):
        return _question_count(obj)

    def get_estimated_minutes(self, obj):
        return obj.estimated_minutes(_question_count(obj))

    def get_my_attempt_count(self, obj):
        return getattr(obj, "my_attempt_count", 0)

    def get_my_best_score(self, obj):
        return getattr(obj, "my_best_score", None)


class TestDetailSerializer(TestSummarySerializer):
    """The Test instructions page: questions plus the student's resume/start state."""

    questions = QuestionSerializer(many=True, read_only=True)
    in_progress_attempt_id = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()

    class Meta(TestSummarySerializer.Meta):
        fields = TestSummarySerializer.Meta.fields + ("questions", "in_progress_attempt_id", "can_start")

    def _attempts(self, obj):
        user = self.context["request"].user
        return Attempt.objects.filter(student=user, test=obj)

    def get_in_progress_attempt_id(self, obj):
        attempt = self._attempts(obj).filter(status=Attempt.Status.IN_PROGRESS).only("id").first()
        return attempt.id if attempt else None

    def get_can_start(self, obj):
        if obj.status != MockTest.Status.PUBLISHED or not _question_count(obj):
            return False
        return obj.allow_retake or not self._attempts(obj).filter(status__in=FINISHED_STATUSES).exists()


# ---------------------------------------------------------------------------
# Admin views
# ---------------------------------------------------------------------------
ARCHIVED_QUESTIONS_MESSAGE = "This test is archived. Move it back to draft before editing questions."


class AdminQuestionSerializer(serializers.ModelSerializer):
    time_limit = serializers.IntegerField(read_only=True)

    class Meta:
        model = Question
        fields = ("id", "test", "order", "text", "hint", "answer_seconds", "time_limit", "created_at", "updated_at")
        read_only_fields = ("created_at", "updated_at")

    def validate_text(self, value):
        value = value.strip()
        if len(value) < 5:
            raise serializers.ValidationError("Write the question in at least 5 characters.")
        if len(value) > 1000:
            raise serializers.ValidationError("Keep the question under 1,000 characters.")
        return value

    def validate_hint(self, value):
        return value.strip()

    def validate_test(self, test):
        if self.instance and test.pk != self.instance.test_id:
            raise serializers.ValidationError("A question can't move to another test.")
        if test.status == MockTest.Status.ARCHIVED:
            raise serializers.ValidationError(ARCHIVED_QUESTIONS_MESSAGE)
        return test

    def validate(self, attrs):
        # Also covers edits that don't send "test" (PATCH of the text, hint or time).
        test = attrs.get("test") or getattr(self.instance, "test", None)
        if test is not None and test.status == MockTest.Status.ARCHIVED:
            raise serializers.ValidationError({"test": ARCHIVED_QUESTIONS_MESSAGE})
        return attrs


class EditableTestField(serializers.PrimaryKeyRelatedField):
    """A test whose questions can still change (not archived)."""

    def to_internal_value(self, data):
        test = super().to_internal_value(data)
        if test.status == MockTest.Status.ARCHIVED:
            raise serializers.ValidationError(ARCHIVED_QUESTIONS_MESSAGE)
        return test


class GenerateQuestionsSerializer(serializers.Serializer):
    test = EditableTestField(queryset=MockTest.objects.all())
    count = serializers.IntegerField(min_value=1, max_value=10, default=3)
    topic = serializers.CharField(max_length=150, required=False, allow_blank=True, trim_whitespace=True)


class NewQuestionSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
    hint = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    answer_seconds = serializers.IntegerField(min_value=10, max_value=300, required=False, allow_null=True, default=None)

    def validate_text(self, value):
        value = " ".join(value.split())
        if len(value) < 5:
            raise serializers.ValidationError("Write the question in at least 5 characters.")
        return value

    def validate_hint(self, value):
        return " ".join(value.split())


class BulkQuestionsSerializer(serializers.Serializer):
    test = EditableTestField(queryset=MockTest.objects.all())
    questions = NewQuestionSerializer(many=True, allow_empty=False, max_length=20)


class AiWriteSerializer(serializers.Serializer):
    """The AI generator page: questions (and optionally a title) from a topic."""

    topic = serializers.CharField(max_length=300)
    level = serializers.ChoiceField(choices=User.Level.choices, default=User.Level.INTERMEDIATE)
    count = serializers.IntegerField(min_value=1, max_value=10, default=5)
    answer_seconds = serializers.IntegerField(min_value=10, max_value=300, default=60)
    style = serializers.ChoiceField(choices=[(key, key) for key in STYLES], default="mixed")
    with_title = serializers.BooleanField(default=False)
    test = EditableTestField(queryset=MockTest.objects.all(), required=False, allow_null=True, default=None)
    exclude = serializers.ListField(child=serializers.CharField(max_length=1000), required=False, max_length=60, default=list)

    def validate_topic(self, value):
        value = " ".join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError("Describe the topic in a few words.")
        return value


class AiCreateTestSerializer(serializers.Serializer):
    """Save the AI generator's result as a new draft test with its questions."""

    title = serializers.CharField(max_length=150)
    description = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    level = serializers.ChoiceField(choices=User.Level.choices, default=User.Level.INTERMEDIATE)
    prep_seconds = serializers.IntegerField(min_value=0, max_value=300, default=15)
    answer_seconds = serializers.IntegerField(min_value=10, max_value=300, default=60)
    allow_retake = serializers.BooleanField(default=True)
    questions = NewQuestionSerializer(many=True, allow_empty=False, max_length=20)

    def validate_title(self, value):
        value = " ".join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError("Give the test a title of at least 3 characters.")
        return value


class AdminTestSerializer(serializers.ModelSerializer):
    question_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MockTest
        fields = (
            "id",
            "title",
            "description",
            "level",
            "status",
            "prep_seconds",
            "answer_seconds",
            "allow_retake",
            "question_count",
            "attempt_count",
            "average_score",
            "created_by_name",
            "published_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("published_at", "created_at", "updated_at")

    def get_question_count(self, obj):
        return _question_count(obj)

    def get_attempt_count(self, obj):
        count = getattr(obj, "attempt_count", None)
        return obj.attempts.filter(status__in=FINISHED_STATUSES).count() if count is None else count

    def get_average_score(self, obj):
        value = getattr(obj, "average_score", None)
        return round(value) if value is not None else None

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None

    def validate_title(self, value):
        value = " ".join(value.split())
        if len(value) < 3:
            raise serializers.ValidationError("Give the test a title of at least 3 characters.")
        return value

    def validate(self, attrs):
        status = attrs.get("status", getattr(self.instance, "status", MockTest.Status.DRAFT))
        if status == MockTest.Status.PUBLISHED:
            has_questions = self.instance is not None and self.instance.questions.exists()
            if not has_questions:
                raise serializers.ValidationError({"status": "Add at least one question before publishing this test."})
        return attrs
