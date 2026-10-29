"""
AI-written speaking questions: admins fill a test in one click, and students get fresh
questions in Quick practice. Uses the same AI service as the feedback (Groq, Claude, Gemini backup).

In demo mode (EVALUATION_DEMO_MODE=True) the questions come from the built-in bank below,
so the feature works without any API key.
"""

import json
import random
import re

from django.conf import settings

from apps.common.utils import ServiceError

from . import feedback
from .speech_to_text import EvaluationError, EvaluationNotConfigured

MAX_QUESTIONS = 10

# Topics students can choose in Quick practice (slug -> label). Also used to tag the demo bank.
TOPICS = {
    "daily-life": "Daily life",
    "travel": "Travel and places",
    "work-study": "Work and study",
    "technology": "Technology",
    "health": "Health and sport",
    "environment": "Environment",
    "culture": "Culture and festivals",
    "food": "Food and cooking",
    "interview": "Job interview",
}

SYSTEM_PROMPT = "\n".join(
    [
        "You write speaking-test questions for English learners using the Voice Mock Test app.",
        "Each question must be answerable by speaking for the given number of seconds, without any preparation material.",
        "Rules: open questions (never yes/no); one clear task per question; plain words that suit the student level; "
        "ask for reasons, examples or a description so the student can speak at length; "
        "no politics, religion, health conditions, money troubles or other sensitive personal topics; "
        "do not repeat or closely copy any question in existing_questions; every question in your list must be different.",
        "hint: what a good answer could include, at most 12 words, no full stop needed.",
        'Reply with one JSON object and nothing else: {"questions":[{"text":"...","hint":"..."}]}',
    ]
)

LEVEL_GUIDE = {
    "beginner": "Beginner (A2): everyday topics, simple present and past, very familiar situations.",
    "intermediate": "Intermediate (B1-B2): opinions with reasons, comparisons, past experiences and plans.",
    "advanced": "Advanced (C1): abstract topics, evaluating both sides, hypotheses and detailed explanations.",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def write_questions(
    *,
    count: int = 3,
    level: str = "intermediate",
    topic: str = "",
    title: str = "",
    description: str = "",
    existing=(),
    answer_seconds: int = 60,
) -> tuple[list[dict], bool]:
    """Return ([{"text", "hint"}, ...], is_demo). Raises ServiceError with a plain message if the AI can't help."""
    count = max(1, min(MAX_QUESTIONS, int(count)))
    existing = [text for text in existing if text]
    if settings.EVALUATION_DEMO_MODE:
        return demo_questions(count=count, level=level, topic=topic or title, existing=existing), True

    request = {
        "number_of_questions": count,
        "student_level": LEVEL_GUIDE.get(level, level or "any level"),
        "topic": topic or title or "everyday life",
        "test_title": title,
        "test_description": description,
        "speaking_time_seconds": answer_seconds,
        "existing_questions": existing[-40:],
    }
    try:
        reply = feedback.call_model(SYSTEM_PROMPT, json.dumps(request), max_tokens=300 + 120 * count, temperature=0.8)
    except EvaluationNotConfigured:
        raise ServiceError(
            "AI question writing isn't set up yet. Add the AI key (GROQ_API_KEY) on the server, or turn on demo mode.",
            status_code=503,
        ) from None
    except EvaluationError:
        raise ServiceError("The AI service is busy right now. Try again in a minute.", status_code=502) from None

    questions = clean_questions((reply or {}).get("questions"), existing)[:count]
    if not questions:
        raise ServiceError("The AI didn't return usable questions. Try again, or change the topic.", status_code=502)
    return questions, False


def clean_questions(items, existing=()) -> list[dict]:
    """Keep well-formed, new questions: trimmed text (10-300 characters), short hint, no duplicates."""
    if not isinstance(items, list):
        return []
    seen = {_key(text) for text in existing}
    questions = []
    for item in items:
        if isinstance(item, str):
            item = {"text": item}
        if not isinstance(item, dict):
            continue
        text = _tidy(item.get("text"))
        text = re.sub(r"^(?:q(?:uestion)?\s*)?\d+\s*[.):-]\s*", "", text, flags=re.IGNORECASE)  # "1. ", "Q2) "
        hint = _tidy(item.get("hint"))[:120]
        if not 10 <= len(text) <= 300 or _key(text) in seen:
            continue
        seen.add(_key(text))
        questions.append({"text": text, "hint": hint})
    return questions


# ---------------------------------------------------------------------------
# Demo bank
# ---------------------------------------------------------------------------
DEMO_BANK = [
    ("daily-life", "beginner", "Describe a normal day in your life, from morning to evening.", "Morning routine, study or work, evening"),
    ("daily-life", "beginner", "Talk about your home. What do you like most about it?", "Rooms, people you live with, favourite place"),
    ("daily-life", "intermediate", "How do you usually spend your weekends, and why?", "Activities, people, what makes it relaxing"),
    ("daily-life", "intermediate", "Describe a habit you would like to change and explain how you could do it.", "The habit, why change it, your plan"),
    ("daily-life", "advanced", "Some people say modern life is too busy. Do you agree? Explain your view.", "Examples, causes, possible solutions"),
    ("travel", "beginner", "Describe a place you like to visit in your town.", "Where it is, what you do there, why you like it"),
    ("travel", "beginner", "Talk about a trip you took with your family or friends.", "Where you went, what you did, how you felt"),
    ("travel", "intermediate", "Which country would you most like to visit, and why?", "Places, food, culture, what you hope to learn"),
    ("travel", "intermediate", "Describe the best way for a visitor to see your country.", "Transport, places to see, best time to go"),
    ("travel", "advanced", "How does tourism change a small town? Talk about the good and bad effects.", "Jobs, prices, culture, environment"),
    ("work-study", "beginner", "Talk about your favourite subject at school or college.", "What you learn, the teacher, why you enjoy it"),
    ("work-study", "intermediate", "Describe a skill you learned recently and how you learned it.", "The skill, the steps, what was difficult"),
    ("work-study", "intermediate", "What job would you like to have in five years, and why?", "The job, the skills you need, your plan"),
    ("work-study", "advanced", "Is it better to work for a large company or a small one? Explain your opinion.", "Pay, learning, freedom, security"),
    ("technology", "beginner", "How do you use your phone every day?", "Apps, messages, study, entertainment"),
    ("technology", "intermediate", "Describe a piece of technology that has made your life easier.", "What it is, how you use it, what changed"),
    ("technology", "advanced", "Should children be allowed to use social media? Give reasons for your answer.", "Benefits, risks, age, rules"),
    ("health", "beginner", "Talk about a sport or exercise you enjoy.", "What it is, how often, who with"),
    ("health", "intermediate", "What do you do to stay healthy, and what could you do better?", "Food, sleep, exercise, one change"),
    ("health", "advanced", "Why do many people find it hard to live a healthy lifestyle? Suggest some solutions.", "Time, money, habits, ideas that help"),
    ("environment", "beginner", "What do you do to keep your town clean?", "Rubbish, recycling, water, small actions"),
    ("environment", "intermediate", "Describe an environmental problem in your area and how people could solve it.", "The problem, causes, solutions"),
    ("environment", "advanced", "Who should do more to protect the environment: governments or individuals?", "Laws, habits, examples, your view"),
    ("culture", "beginner", "Describe your favourite festival and how you celebrate it.", "When it is, food, clothes, activities"),
    ("culture", "intermediate", "Talk about a tradition in your family that is important to you.", "What happens, who takes part, why it matters"),
    ("culture", "advanced", "How is your culture changing for young people? Is this a good thing?", "Examples, reasons, good and bad sides"),
    ("food", "beginner", "What is your favourite meal and how is it made?", "Ingredients, steps, when you eat it"),
    ("food", "intermediate", "Describe a meal you remember well and explain why it was special.", "Place, people, food, feelings"),
    ("food", "advanced", "Is fast food a problem in your country? Explain your opinion.", "Health, cost, habits, alternatives"),
    ("interview", "beginner", "Introduce yourself. Tell me about your studies and your interests.", "Name, home town, studies, hobbies"),
    ("interview", "intermediate", "Tell me about a time you worked in a team. What was your role?", "The task, your part, the result"),
    ("interview", "intermediate", "What are your greatest strengths, and how have you used them?", "Two strengths with real examples"),
    ("interview", "advanced", "Describe a difficult problem you solved and what you learned from it.", "The situation, your actions, the result"),
]


def demo_questions(*, count: int, level: str = "", topic: str = "", existing=()) -> list[dict]:
    """Questions from the built-in bank: the requested topic and level first, never one already in the test."""
    seen = {_key(text) for text in existing}
    topic_slug = _topic_slug(topic)
    pool = [entry for entry in DEMO_BANK if _key(entry[2]) not in seen]
    rng = random.Random()
    rng.shuffle(pool)
    pool.sort(key=lambda entry: (entry[0] != topic_slug, entry[1] != level))  # best matches first, random within
    return [{"text": text, "hint": hint} for _topic, _level, text, hint in pool[:count]]


def _topic_slug(topic: str) -> str:
    if topic in TOPICS:
        return topic
    words = set(re.findall(r"[a-z]+", (topic or "").lower()))
    for slug, label in TOPICS.items():
        if words & set(re.findall(r"[a-z]+", label.lower())) - {"and"}:
            return slug
    return ""


def _tidy(value) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
