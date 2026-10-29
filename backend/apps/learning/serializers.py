from rest_framework import serializers

from apps.evaluation.question_writer import TOPICS

from .models import PracticeAnswer


class PracticeAnswerSerializer(serializers.ModelSerializer):
    audio_url = serializers.SerializerMethodField()
    topic_label = serializers.SerializerMethodField()

    class Meta:
        model = PracticeAnswer
        fields = (
            "id",
            "topic",
            "topic_label",
            "source",
            "question_text",
            "hint",
            "time_limit",
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
            "score_notes",
            "is_demo",
            "created_at",
        )
        read_only_fields = fields

    def get_audio_url(self, obj):
        if not obj.audio:
            return None
        url = obj.audio.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request and url.startswith("/") else url

    def get_topic_label(self, obj):
        return TOPICS.get(obj.topic, "")


class PracticeQuestionRequestSerializer(serializers.Serializer):
    source = serializers.ChoiceField(choices=PracticeAnswer.Source.choices, default=PracticeAnswer.Source.AI)
    topic = serializers.ChoiceField(choices=[("", "Any"), *TOPICS.items()], required=False, allow_blank=True, default="")


class PracticeUploadSerializer(serializers.Serializer):
    audio = serializers.FileField(allow_empty_file=True)
    question_text = serializers.CharField(max_length=1000)
    hint = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    topic = serializers.ChoiceField(choices=[("", "Any"), *TOPICS.items()], required=False, allow_blank=True, default="")
    source = serializers.ChoiceField(choices=PracticeAnswer.Source.choices, default=PracticeAnswer.Source.AI)
    time_limit = serializers.IntegerField(min_value=10, max_value=300, default=60)
    duration_seconds = serializers.FloatField(required=False, min_value=0, max_value=900)

    def validate_question_text(self, value):
        value = " ".join(value.split())
        if len(value) < 5:
            raise serializers.ValidationError("The question is missing. Get a new question and try again.")
        return value


class NotebookMarkSerializer(serializers.Serializer):
    key = serializers.RegexField(r"^[0-9a-f]{40}$")
    learned = serializers.BooleanField()
