"""
Scoring rules for spoken answers.

    fluency        = 70% delivery (pace, filler words, long pauses) + 30% coherence (Claude)
    pronunciation  = audio clarity from the speech-to-text confidence
                     (Claude's estimate when the transcriber gives no confidence values)
    grammar        = Claude
    overall        = weighted average of the three skills (SCORING["WEIGHTS"] in settings)

An answer is flagged for review when the score is under the threshold, the answer is
very short, the audio was hard to hear, or it looks off topic.
"""

import re
from dataclasses import asdict, dataclass

from django.conf import settings

from apps.common.utils import average, clamp_score, weighted_average

from . import feedback
from .speech_to_text import Transcript, transcribe

SKILLS = ("fluency", "pronunciation", "grammar")
FILLER_PATTERN = re.compile(r"\b(?:um+|uh+|erm+|er|ah+|hmm+|you know|i mean)\b", re.IGNORECASE)


def rules() -> dict:
    return settings.SCORING


@dataclass
class DeliveryMetrics:
    duration_seconds: float
    word_count: int
    words_per_minute: int
    filler_count: int
    long_pauses: int
    clarity: int | None
    fluency_auto: int


@dataclass
class AnswerEvaluation:
    transcript: str
    duration_seconds: float
    word_count: int
    words_per_minute: int
    filler_count: int
    long_pauses: int
    clarity: int | None
    fluency: int
    pronunciation: int
    grammar: int
    coherence: int
    relevance: int
    overall: int
    strengths: list
    tip: str
    corrections: list
    review_reasons: list
    is_demo: bool = False

    @property
    def needs_review(self) -> bool:
        return bool(self.review_reasons)

    def as_model_fields(self) -> dict:
        """Field values for an attempts.Answer row."""
        return {**asdict(self), "needs_review": self.needs_review}


# ---------------------------------------------------------------------------
# Delivery measurements
# ---------------------------------------------------------------------------
def measure_delivery(transcript: Transcript, recorded_seconds: float | None = None) -> DeliveryMetrics:
    r = rules()
    words = transcript.words
    segments = transcript.segments

    duration = transcript.duration or recorded_seconds or (segments[-1].end if segments else 0) or 60
    start = segments[0].start if segments else 0
    end = segments[-1].end if segments else duration
    speaking_seconds = max(1.0, end - start)

    wpm = round(len(words) / (speaking_seconds / 60))
    fillers = len(FILLER_PATTERN.findall(transcript.text))
    long_pauses = sum(
        1 for previous, current in zip(segments, segments[1:]) if current.start - previous.end > r["LONG_PAUSE_SECONDS"]
    )

    low, high = r["IDEAL_WPM_MIN"], r["IDEAL_WPM_MAX"]
    if low <= wpm <= high:
        pace = 100
    elif wpm < low:
        pace = 100 - (low - wpm) * 1.2
    else:
        pace = 100 - (wpm - high)
    fillers_per_100_words = fillers / max(1, len(words)) * 100
    fluency_auto = clamp_score(
        clamp_score(pace) * 0.6
        + clamp_score(100 - fillers_per_100_words * 8) * 0.25
        + clamp_score(100 - long_pauses * 15) * 0.15
    )

    return DeliveryMetrics(
        duration_seconds=round(float(duration), 1),
        word_count=len(words),
        words_per_minute=wpm,
        filler_count=fillers,
        long_pauses=long_pauses,
        clarity=_clarity(segments),
        fluency_auto=fluency_auto,
    )


def _clarity(segments):
    """0-100 from the transcriber's confidence, weighted by segment length."""
    scored = [segment for segment in segments if segment.avg_logprob is not None]
    if not scored:
        return None
    lengths = [max(0.01, segment.end - segment.start) for segment in scored]
    log_probability = sum(segment.avg_logprob * length for segment, length in zip(scored, lengths)) / sum(lengths)
    no_speech = max(segment.no_speech_prob or 0 for segment in scored)
    return clamp_score(100 + (log_probability + 0.15) * 70 - max(0, no_speech - 0.5) * 60)


# ---------------------------------------------------------------------------
# Scores and review rules
# ---------------------------------------------------------------------------
def overall_score(fluency, pronunciation, grammar, weights: dict | None = None):
    values = {"fluency": fluency, "pronunciation": pronunciation, "grammar": grammar}
    return weighted_average(values, weights or rules()["WEIGHTS"])


def headline_for(overall) -> str:
    if overall is None:
        return ""
    if overall >= 80:
        return "Great job!"
    if overall >= 60:
        return "Good progress"
    return "Keep practising"


def answer_review_reasons(*, overall, word_count, clarity, relevance) -> list[str]:
    r = rules()
    reasons = []
    if overall is not None and overall < r["REVIEW_THRESHOLD"]:
        reasons.append(f"Score under {r['REVIEW_THRESHOLD']}%")
    if word_count < r["MIN_WORDS"]:
        reasons.append("Very short answer")
    if clarity is not None and clarity < r["MIN_CLARITY"]:
        reasons.append("Audio was hard to hear")
    if relevance is not None and relevance < r["MIN_RELEVANCE"]:
        reasons.append("Answer may be off topic")
    return reasons


def attempt_review_reasons(overall, answers) -> list[str]:
    """Reasons to flag a whole attempt: a low overall score or any flagged answer."""
    threshold = rules()["REVIEW_THRESHOLD"]
    reasons = []
    if overall is not None and overall < threshold:
        reasons.append(f"Overall score under {threshold}%")
    for answer in answers:
        for reason in answer.review_reasons or []:
            reasons.append(f"Question {answer.question_order}: {reason}")
    return reasons


def summarise_scores(answers) -> dict:
    """Average skill scores across an attempt's answers, plus overall and headline."""
    skills = {skill: average(getattr(answer, skill) for answer in answers) for skill in SKILLS}
    overall = overall_score(**skills)
    return {**skills, "overall": overall, "headline": headline_for(overall)}


# ---------------------------------------------------------------------------
# Full pipeline for one answer
# ---------------------------------------------------------------------------
def evaluate_answer(
    audio,
    *,
    question_text: str,
    level: str = "",
    recorded_seconds: float | None = None,
    filename: str = "answer.webm",
    content_type: str = "audio/webm",
) -> AnswerEvaluation:
    """Transcribe, measure and score one recorded answer."""
    transcript = transcribe(audio, filename=filename, content_type=content_type)
    metrics = measure_delivery(transcript, recorded_seconds)
    analysis = feedback.analyse_answer(
        question=question_text,
        transcript=transcript.text,
        level=level,
        measurements={
            "words": metrics.word_count,
            "words_per_minute": metrics.words_per_minute,
            "filler_words": metrics.filler_count,
            "long_pauses": metrics.long_pauses,
            "audio_clarity_0_100": metrics.clarity,
        },
    )

    fluency = clamp_score(metrics.fluency_auto * 0.7 + analysis["coherence"] * 0.3)
    pronunciation = metrics.clarity if metrics.clarity is not None else analysis["pronunciation_estimate"]
    grammar = analysis["grammar"]
    overall = overall_score(fluency, pronunciation, grammar)

    return AnswerEvaluation(
        transcript=transcript.text,
        duration_seconds=metrics.duration_seconds,
        word_count=metrics.word_count,
        words_per_minute=metrics.words_per_minute,
        filler_count=metrics.filler_count,
        long_pauses=metrics.long_pauses,
        clarity=metrics.clarity,
        fluency=fluency,
        pronunciation=pronunciation,
        grammar=grammar,
        coherence=analysis["coherence"],
        relevance=analysis["relevance"],
        overall=overall,
        strengths=analysis["strengths"],
        tip=analysis["tip"],
        corrections=analysis["corrections"],
        review_reasons=answer_review_reasons(
            overall=overall,
            word_count=metrics.word_count,
            clarity=metrics.clarity,
            relevance=analysis["relevance"],
        ),
        is_demo=transcript.is_demo,
    )
