"""
python manage.py seed_demo

Adds three published sample tests with questions. In development (DJANGO_DEBUG=True)
it also creates a demo student account. The admin account is created by `migrate`.
Running it again changes nothing that already exists.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.tests_manager.models import MockTest, Question

DEMO_STUDENT = {"email": "student@example.com", "password": "student123", "full_name": "Aarati Sharma"}

SAMPLE_TESTS = [
    {
        "title": "Everyday conversation",
        "description": "Talk about your daily life, places you like and the people around you.",
        "level": User.Level.BEGINNER,
        "prep_seconds": 15,
        "answer_seconds": 60,
        "questions": [
            ("Introduce yourself. Where are you from and what do you do?", "Your name, home town, studies or work."),
            ("Describe your favourite place and explain why you enjoy visiting it.", "Where is it? What do you do there?"),
            ("Talk about a friend you admire.", "How did you meet? What makes them special?"),
            ("What do you usually do at the weekend?", "Give one or two examples."),
        ],
    },
    {
        "title": "Travel and places",
        "description": "Describe trips, compare places and give your opinion about travel.",
        "level": User.Level.INTERMEDIATE,
        "prep_seconds": 20,
        "answer_seconds": 60,
        "questions": [
            ("Describe a trip you enjoyed. Where did you go and what did you do?", "Use past tenses."),
            ("Compare life in a big city with life in a small town.", "Give at least two differences."),
            ("Some people prefer to travel alone. What do you prefer, and why?", "Give a reason and an example."),
            ("Which place in your country would you recommend to a visitor?", "Explain what makes it worth visiting."),
        ],
    },
    {
        "title": "Job interview practice",
        "description": "Answer common interview questions clearly and with examples.",
        "level": User.Level.ADVANCED,
        "prep_seconds": 30,
        "answer_seconds": 90,
        "questions": [
            ("Tell me about yourself and why you are interested in this role.", "Keep it relevant to the job."),
            ("Describe a challenge you faced in a project and how you solved it.", "Situation, action, result."),
            ("What is one of your strengths, and how has it helped you?", "Support it with an example."),
            ("Where do you see yourself in five years?", "Be realistic and specific."),
            ("Do you have any questions for us?", "Ask about the team, the work or how success is measured."),
        ],
    },
]


class Command(BaseCommand):
    help = "Adds sample tests (and a demo student in development) so the app can be tried straight away."

    def add_arguments(self, parser):
        parser.add_argument("--no-users", action="store_true", help="Only add the sample tests.")

    @transaction.atomic
    def handle(self, *args, **options):
        admin = User.objects.filter(role=User.Role.ADMIN).order_by("id").first()
        student = None
        if options["no_users"]:
            self.stdout.write("Skipping the demo student (--no-users).")
        elif not settings.DEBUG:
            self.stdout.write(self.style.WARNING("DJANGO_DEBUG is False, so no demo student was created."))
        else:
            student = self._ensure_user(DEMO_STUDENT, role=User.Role.STUDENT)

        created_tests = 0
        for sample in SAMPLE_TESTS:
            if MockTest.objects.filter(title=sample["title"]).exists():
                continue
            test = MockTest.objects.create(
                title=sample["title"],
                description=sample["description"],
                level=sample["level"],
                prep_seconds=sample["prep_seconds"],
                answer_seconds=sample["answer_seconds"],
                created_by=admin,
            )
            for order, (text, hint) in enumerate(sample["questions"], start=1):
                Question.objects.create(test=test, order=order, text=text, hint=hint)
            test.status = MockTest.Status.PUBLISHED
            test.save()
            created_tests += 1

        existing = len(SAMPLE_TESTS) - created_tests
        message = f"Sample tests added: {created_tests}." + (f" {existing} already existed." if existing else "")
        self.stdout.write(self.style.SUCCESS(message))
        self.stdout.write("")
        if admin:
            # Show the starting password only on a development computer, never in hosting build logs.
            show = settings.DEBUG and admin.uses_default_password
            default = " / " + settings.DEFAULT_ADMIN_PASSWORD if show else " (your password)"
            self.stdout.write(f"  Admin    {admin.email}{default}")
        else:
            self.stdout.write("  No admin yet: run  python manage.py create_admin")
        if student:
            self.stdout.write(f"  Student  {DEMO_STUDENT['email']} / {DEMO_STUDENT['password']}  (demo, development only)")

    def _ensure_user(self, data, **extra):
        user = User.objects.filter(email=data["email"]).first()
        if user:
            return user
        return User.objects.create_user(
            email=data["email"], password=data["password"], full_name=data["full_name"], **extra
        )
