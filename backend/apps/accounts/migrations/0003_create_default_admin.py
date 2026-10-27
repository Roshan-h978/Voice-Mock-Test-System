"""Creates the first admin account so the app can be used straight after `migrate`.

Email and password come from DEFAULT_ADMIN_EMAIL / DEFAULT_ADMIN_PASSWORD in backend/.env
(default admin@example.com / admin123). Nothing is created if an admin already exists.
Change the password after the first sign-in (Profile > Change password).
"""

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_default_admin(apps, schema_editor):
    if getattr(settings, "TESTING", False):
        return  # test databases start empty
    User = apps.get_model("accounts", "User")
    if User.objects.filter(role="admin").exists() or User.objects.filter(is_superuser=True).exists():
        return
    email = settings.DEFAULT_ADMIN_EMAIL
    if User.objects.filter(email=email).exists():
        return
    User.objects.create(
        email=email,
        full_name=settings.DEFAULT_ADMIN_NAME,
        role="admin",
        level="advanced",
        is_staff=True,
        is_superuser=True,
        is_active=True,
        password=make_password(settings.DEFAULT_ADMIN_PASSWORD),
        uses_default_password=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0002_user_uses_default_password"),
    ]

    operations = [
        migrations.RunPython(create_default_admin, migrations.RunPython.noop),
    ]
