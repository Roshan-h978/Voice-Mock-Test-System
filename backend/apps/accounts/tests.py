"""Tests for sign-up, sign-in, profiles, password reset, invitations and admin user management."""

import importlib
import re
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.apps import apps as django_apps
from django.core import mail
from django.core.management import call_command
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.notifications.email_service import EmailDeliveryError

from .models import AccountToken, User

PASSWORD = "Speak-Clearly-2026"
TOKEN_IN_LINK = re.compile(r"(?:token|invite)=([0-9a-f]{64})")


def make_user(email="aarati@example.com", role=User.Role.STUDENT, full_name="Aarati Sharma", **extra):
    return User.objects.create_user(email=email, password=PASSWORD, full_name=full_name, role=role, **extra)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    EMAIL_DELIVERY="django",
    ALLOW_PUBLIC_REGISTRATION=True,
)
class AccountTestCase(APITestCase):
    def setUp(self):
        cache.clear()  # reset rate limits between tests


class RegisterAndLoginTests(AccountTestCase):
    def test_register_creates_a_student_and_returns_tokens(self):
        response = self.client.post(
            reverse("auth-register"),
            {"full_name": "  Aarati   Sharma ", "email": "Aarati@Example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "aarati@example.com")
        self.assertEqual(response.data["user"]["full_name"], "Aarati Sharma")
        self.assertEqual(response.data["user"]["role"], User.Role.STUDENT)

    def test_register_rejects_an_existing_email_in_any_case(self):
        make_user()
        response = self.client.post(
            reverse("auth-register"),
            {"full_name": "Someone Else", "email": "AARATI@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_register_rejects_a_weak_password(self):
        response = self.client.post(
            reverse("auth-register"),
            {"full_name": "Aarati Sharma", "email": "aarati@example.com", "password": "12345678"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    @override_settings(ALLOW_PUBLIC_REGISTRATION=False)
    def test_register_needs_an_invitation_when_sign_up_is_closed(self):
        response = self.client.post(
            reverse("auth-register"),
            {"full_name": "Aarati Sharma", "email": "aarati@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.exists())

    def test_login_returns_tokens_and_the_user(self):
        make_user()
        response = self.client.post(
            reverse("auth-login"), {"email": " AARATI@example.com ", "password": PASSWORD}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertEqual(response.data["user"]["full_name"], "Aarati Sharma")

    def test_login_with_a_wrong_password_fails(self):
        make_user()
        response = self.client.post(reverse("auth-login"), {"email": "aarati@example.com", "password": "nope"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_suspended_user_cannot_sign_in(self):
        make_user(is_active=False)
        response = self.client.post(reverse("auth-login"), {"email": "aarati@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_and_logout(self):
        make_user()
        tokens = self.client.post(
            reverse("auth-login"), {"email": "aarati@example.com", "password": PASSWORD}, format="json"
        ).data
        refreshed = self.client.post(reverse("auth-refresh"), {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", refreshed.data)  # rotated

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refreshed.data['access']}")
        logout = self.client.post(reverse("auth-logout"), {"refresh": refreshed.data["refresh"]}, format="json")
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT)
        again = self.client.post(reverse("auth-refresh"), {"refresh": refreshed.data["refresh"]}, format="json")
        self.assertEqual(again.status_code, status.HTTP_401_UNAUTHORIZED)


class ProfileTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def test_get_and_update_profile(self):
        self.assertEqual(self.client.get(reverse("auth-me")).data["email"], "aarati@example.com")
        response = self.client.patch(
            reverse("auth-me"), {"full_name": "Aarati S. Sharma", "level": "intermediate", "role": "admin"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["level"], "intermediate")
        self.assertEqual(response.data["role"], User.Role.STUDENT)  # role can't be changed here

    def test_change_password(self):
        wrong = self.client.post(
            reverse("auth-change-password"),
            {"current_password": "wrong", "new_password": "Another-Strong-2026"},
            format="json",
        )
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(
            reverse("auth-change-password"),
            {"current_password": PASSWORD, "new_password": "Another-Strong-2026"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Another-Strong-2026"))

    def test_google_account_without_a_password_is_told_how_to_set_one(self):
        self.user.set_unusable_password()
        self.user.save()
        response = self.client.post(
            reverse("auth-change-password"),
            {"current_password": "anything", "new_password": "Another-Strong-2026"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Forgot password?", str(response.data["current_password"]))

    def test_profile_needs_sign_in(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, status.HTTP_401_UNAUTHORIZED)


class PasswordResetTests(AccountTestCase):
    def test_full_reset_flow(self):
        user = make_user()
        response = self.client.post(reverse("auth-password-reset"), {"email": "Aarati@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        token = TOKEN_IN_LINK.search(mail.outbox[0].body).group(1)

        confirm = self.client.post(
            reverse("auth-password-reset-confirm"), {"token": token, "new_password": "Fresh-Start-2026"}, format="json"
        )
        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password("Fresh-Start-2026"))

        reused = self.client.post(
            reverse("auth-password-reset-confirm"), {"token": token, "new_password": "Fresh-Start-2027"}, format="json"
        )
        self.assertEqual(reused.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_email_gets_the_same_answer_and_no_email(self):
        response = self.client.post(reverse("auth-password-reset"), {"email": "nobody@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_only_the_newest_reset_link_works(self):
        make_user()
        self.client.post(reverse("auth-password-reset"), {"email": "aarati@example.com"}, format="json")
        self.client.post(reverse("auth-password-reset"), {"email": "aarati@example.com"}, format="json")
        first = TOKEN_IN_LINK.search(mail.outbox[0].body).group(1)
        response = self.client.post(
            reverse("auth-password-reset-confirm"), {"token": first, "new_password": "Fresh-Start-2026"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InvitationTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user("nisha@example.com", role=User.Role.ADMIN, full_name="Nisha Adhikari")

    def invite(self, **body):
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse("admin-users-invite"), body, format="json")
        self.client.force_authenticate(None)
        return response

    def test_invited_admin_registers_with_the_admin_role(self):
        response = self.invite(email="sita@example.com", full_name="Sita Rai", role="admin")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["email_sent"])
        token = TOKEN_IN_LINK.search(mail.outbox[0].body).group(1)

        info = self.client.get(reverse("auth-invitation", args=[token]))
        self.assertEqual(info.data["email"], "sita@example.com")
        self.assertEqual(info.data["role"], "admin")

        register = self.client.post(
            reverse("auth-register"),
            {"full_name": "Sita Rai", "email": "sita@example.com", "password": PASSWORD, "invite_token": token},
            format="json",
        )
        self.assertEqual(register.status_code, status.HTTP_201_CREATED)
        self.assertEqual(register.data["user"]["role"], "admin")
        self.assertEqual(self.client.get(reverse("auth-invitation", args=[token])).status_code, status.HTTP_404_NOT_FOUND)

    def test_invitation_must_be_used_with_the_invited_email(self):
        self.invite(email="sita@example.com")
        token = TOKEN_IN_LINK.search(mail.outbox[0].body).group(1)
        response = self.client.post(
            reverse("auth-register"),
            {"full_name": "Sita Rai", "email": "other@example.com", "password": PASSWORD, "invite_token": token},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_failed_email_returns_the_link_to_share(self):
        with mock.patch("apps.notifications.email_service.send_invitation", side_effect=EmailDeliveryError):
            response = self.invite(email="sita@example.com")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["email_sent"])
        self.assertIn("/register?invite=", response.data["invite_link"])

    def test_students_cannot_invite(self):
        self.client.force_authenticate(make_user())
        response = self.client.post(reverse("admin-users-invite"), {"email": "x@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tokens_are_stored_as_hashes(self):
        self.invite(email="sita@example.com")
        token = TOKEN_IN_LINK.search(mail.outbox[0].body).group(1)
        self.assertFalse(AccountToken.objects.filter(token_hash=token).exists())


class AdminUserManagementTests(AccountTestCase):
    def setUp(self):
        super().setUp()
        self.admin = make_user("nisha@example.com", role=User.Role.ADMIN, full_name="Nisha Adhikari")
        self.student = make_user(level="intermediate")
        make_user("bikash@example.com", full_name="Bikash Thapa", is_active=False)
        self.client.force_authenticate(self.admin)

    def test_list_with_filters(self):
        students = self.client.get(reverse("admin-users"), {"role": "student"})
        self.assertEqual(students.data["count"], 2)
        active = self.client.get(reverse("admin-users"), {"role": "student", "status": "active"})
        self.assertEqual([row["email"] for row in active.data["results"]], ["aarati@example.com"])
        search = self.client.get(reverse("admin-users"), {"search": "bikash"})
        self.assertEqual(search.data["count"], 1)

    def test_suspend_a_student(self):
        url = reverse("admin-user-detail", args=[self.student.pk])
        response = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertFalse(self.student.is_active)

    def test_admin_cannot_suspend_or_demote_themselves(self):
        url = reverse("admin-user-detail", args=[self.admin.pk])
        self.assertEqual(self.client.patch(url, {"is_active": False}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(url, {"role": "student"}, format="json").status_code, 400)

    def test_demoting_a_superuser_removes_admin_rights(self):
        boss = User.objects.create_superuser(email="boss@example.com", password=PASSWORD, full_name="Boss", role=User.Role.ADMIN)
        response = self.client.patch(reverse("admin-user-detail", args=[boss.pk]), {"role": "student"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        boss.refresh_from_db()
        self.assertFalse(boss.is_admin)
        self.assertFalse(boss.is_staff or boss.is_superuser)

    def test_students_cannot_list_users(self):
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get(reverse("admin-users")).status_code, status.HTTP_403_FORBIDDEN)

    def test_sorting_by_score_puts_people_without_a_score_last(self):
        from apps.attempts.models import Attempt
        from apps.tests_manager.models import MockTest

        test = MockTest.objects.create(title="Everyday conversation")
        Attempt.objects.create(student=self.student, test=test, status=Attempt.Status.SCORED, overall=72)
        for ordering in ("-score", "score"):
            rows = self.client.get(reverse("admin-users"), {"role": "student", "ordering": ordering}).data["results"]
            self.assertEqual([row["email"] for row in rows], ["aarati@example.com", "bikash@example.com"], ordering)


# ---------------------------------------------------------------------------
# Google sign-in, first admin account
# ---------------------------------------------------------------------------
GOOGLE_CLAIMS = {
    "iss": "https://accounts.google.com",
    "aud": "test-client.apps.googleusercontent.com",
    "email": "sita.rai@gmail.com",
    "email_verified": True,
    "name": "Sita Rai",
}


@override_settings(GOOGLE_CLIENT_ID="test-client.apps.googleusercontent.com", ALLOW_PUBLIC_REGISTRATION=True)
class GoogleSignInTests(AccountTestCase):
    def google(self, claims=None, **body):
        with mock.patch("apps.accounts.google_auth.id_token.verify_token", return_value=claims or GOOGLE_CLAIMS) as verify:
            response = self.client.post(reverse("auth-google"), {"credential": "header.payload.signature", **body}, format="json")
        return response, verify

    def test_config_shows_the_client_id(self):
        response = self.client.get(reverse("auth-google-config"))
        self.assertEqual(response.data["enabled"], True)
        self.assertEqual(response.data["client_id"], "test-client.apps.googleusercontent.com")

    @override_settings(GOOGLE_CLIENT_ID="")
    def test_not_configured(self):
        self.assertEqual(self.client.get(reverse("auth-google-config")).data["enabled"], False)
        response = self.client.post(reverse("auth-google"), {"credential": "x"}, format="json")
        self.assertEqual(response.status_code, 503)

    def test_new_google_user_becomes_a_student(self):
        response, verify = self.google()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["created"])
        self.assertIn("access", response.data)
        self.assertEqual(verify.call_args.kwargs["audience"], "test-client.apps.googleusercontent.com")
        user = User.objects.get(email="sita.rai@gmail.com")
        self.assertEqual((user.full_name, user.role), ("Sita Rai", "student"))
        self.assertFalse(user.has_usable_password())

    def test_existing_account_signs_in(self):
        make_user("sita.rai@gmail.com", full_name="Sita R.")
        response, _ = self.google()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["created"])
        self.assertEqual(User.objects.count(), 1)

    def test_suspended_account_is_refused(self):
        make_user("sita.rai@gmail.com", is_active=False)
        response, _ = self.google()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unverified_email_is_refused(self):
        response, _ = self.google({**GOOGLE_CLAIMS, "email_verified": False})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_issuer_is_refused(self):
        response, _ = self.google({**GOOGLE_CLAIMS, "iss": "https://evil.example.com"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_token_is_refused(self):
        with mock.patch("apps.accounts.google_auth.id_token.verify_token", side_effect=ValueError("Token expired")):
            response = self.client.post(reverse("auth-google"), {"credential": "bad"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(User.objects.exists())

    @override_settings(ALLOW_PUBLIC_REGISTRATION=False)
    def test_invitation_gives_the_admin_role(self):
        admin = make_user("nisha@example.com", role=User.Role.ADMIN)
        _, raw = AccountToken.issue(
            purpose=AccountToken.Purpose.INVITE_ADMIN, email="sita.rai@gmail.com", created_by=admin, lifetime=timedelta(days=7)
        )
        closed, _ = self.google()
        self.assertEqual(closed.status_code, status.HTTP_403_FORBIDDEN)  # no invitation sent -> sign-up closed
        response, _ = self.google(invite_token=raw)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["role"], "admin")


class DefaultAdminTests(AccountTestCase):
    def run_migration_function(self):
        migration = importlib.import_module("apps.accounts.migrations.0003_create_default_admin")
        with override_settings(TESTING=False):
            migration.create_default_admin(django_apps, None)

    def test_first_admin_is_created_once_with_admin123(self):
        self.run_migration_function()
        self.run_migration_function()
        admin = User.objects.get(email="admin@example.com")
        self.assertEqual(User.objects.count(), 1)
        self.assertTrue(admin.is_admin and admin.is_superuser and admin.uses_default_password)
        self.assertTrue(admin.check_password("admin123"))

        login = self.client.post(reverse("auth-login"), {"email": "admin@example.com", "password": "admin123"}, format="json")
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertTrue(login.data["user"]["uses_default_password"])

        self.client.force_authenticate(admin)
        self.client.post(
            reverse("auth-change-password"),
            {"current_password": "admin123", "new_password": "My-New-Admin-Pass-2026"},
            format="json",
        )
        admin.refresh_from_db()
        self.assertFalse(admin.uses_default_password)

    def test_no_default_admin_when_an_admin_exists(self):
        make_user("nisha@example.com", role=User.Role.ADMIN)
        self.run_migration_function()
        self.assertFalse(User.objects.filter(email="admin@example.com").exists())

    def test_create_admin_command(self):
        make_user("teacher@example.com")
        call_command("create_admin", "--email", "teacher@example.com", "--password", "secret99", stdout=StringIO())
        teacher = User.objects.get(email="teacher@example.com")
        self.assertTrue(teacher.is_admin and teacher.check_password("secret99"))
        self.assertFalse(teacher.uses_default_password)
