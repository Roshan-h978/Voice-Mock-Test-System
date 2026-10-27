"""
python manage.py create_admin [--email admin@example.com] [--password admin123] [--name Admin]

Creates an admin account, or makes an existing account an admin with the given password.
Use it if you deleted the first admin or forgot its password.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create an admin account (or reset an existing one to admin with a new password)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=settings.DEFAULT_ADMIN_EMAIL)
        parser.add_argument("--password", default=settings.DEFAULT_ADMIN_PASSWORD)
        parser.add_argument("--name", default=settings.DEFAULT_ADMIN_NAME)

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        if "@" not in email:
            raise CommandError("Enter a valid email address with --email.")
        if len(password) < 6:
            raise CommandError("Use a password of at least 6 characters.")

        user = User.objects.filter(email=email).first()
        created = user is None
        if created:
            user = User(email=email, full_name=options["name"])
        user.role = User.Role.ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.uses_default_password = password == settings.DEFAULT_ADMIN_PASSWORD
        user.save()

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} admin {email}. Sign in with that email and the password you chose."))
