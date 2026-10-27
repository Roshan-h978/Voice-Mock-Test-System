"""Evaluation endpoints for admins: scoring setup status and re-scoring an answer."""

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import IsAdmin
from apps.attempts.models import Answer
from apps.attempts.serializers import AnswerSerializer
from apps.attempts.services import rescore_answer


class EvaluationConfigView(APIView):
    """Shows whether scoring is set up and which rules are in use (no secrets)."""

    permission_classes = [IsAdmin]

    def get(self, request):
        rules = settings.SCORING
        return Response(
            {
                "demo_mode": settings.EVALUATION_DEMO_MODE,
                "speech_to_text_ready": bool(settings.OPENAI_API_KEY),
                "feedback_ready": bool(settings.ANTHROPIC_API_KEY),
                "transcribe_model": settings.TRANSCRIBE_MODEL,
                "scoring_model": settings.SCORING_MODEL,
                "weights": rules["WEIGHTS"],
                "review_threshold": rules["REVIEW_THRESHOLD"],
                "ideal_words_per_minute": [rules["IDEAL_WPM_MIN"], rules["IDEAL_WPM_MAX"]],
                "min_words": rules["MIN_WORDS"],
            }
        )


class RescoreAnswerView(APIView):
    """Runs the scoring again on a saved recording."""

    permission_classes = [IsAdmin]

    def post(self, request, pk):
        answer = get_object_or_404(Answer.objects.select_related("attempt__student"), pk=pk)
        answer = rescore_answer(answer)
        return Response(AnswerSerializer(answer, context={"request": request}).data)
