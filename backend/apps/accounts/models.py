"""Users (students and admins) and one-time account links."""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from apps.common.utils import generate_token, hash_token


class UserManager(BaseUserManager):
    """Creates users with an email address instead of a username."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.STUDENT)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser needs is_staff=True and is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """A student or an admin. People sign in with their email address."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        ADMIN = "admin", "Admin"

    class Level(models.TextChoices):
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    username = None
    first_name = None
    last_name = None

    email = models.EmailField("email address", unique=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.BEGINNER)
    phone = models.CharField(max_length=30, blank=True)
    uses_default_password = models.BooleanField(
        default=False, help_text="True until the first admin changes the password set by the setup migration."
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        ordering = ["full_name", "email"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        super().set_password(raw_password)
        self.uses_default_password = False

    @property
    def is_admin(self) -> bool:
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT and not self.is_superuser

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else self.email


class AccountToken(models.Model):
    """One-time link for an invitation or a password reset.

    Only a SHA-256 hash of the token is stored; the raw token exists only in the emailed link.
    """

    class Purpose(models.TextChoices):
        INVITE_STUDENT = "invite_student", "Student invitation"
        INVITE_ADMIN = "invite_admin", "Admin invitation"
        PASSWORD_RESET = "password_reset", "Password reset"

    INVITATION_PURPOSES = (Purpose.INVITE_STUDENT, Purpose.INVITE_ADMIN)

    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    email = models.EmailField()
    name = models.CharField(max_length=150, blank=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="account_tokens"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["email", "purpose"])]

    def __str__(self):
        return f"{self.get_purpose_display()} for {self.email}"

    @property
    def is_valid(self) -> bool:
        return self.used_at is None and self.expires_at > timezone.now()

    @property
    def role(self) -> str:
        return User.Role.ADMIN if self.purpose == self.Purpose.INVITE_ADMIN else User.Role.STUDENT

    def mark_used(self):
        self.used_at = timezone.now()
        self.save(update_fields=["used_at"])

    @classmethod
    def issue(cls, *, purpose, email, lifetime, name="", user=None, created_by=None):
        """Create a token and return (record, raw_token).

        Older unused tokens for the same email and purpose stop working.
        """
        email = email.strip().lower()
        now = timezone.now()
        cls.objects.filter(email=email, purpose=purpose, used_at__isnull=True).update(used_at=now)
        raw_token = generate_token()
        record = cls.objects.create(
            token_hash=hash_token(raw_token),
            purpose=purpose,
            email=email,
            name=name,
            user=user,
            created_by=created_by,
            expires_at=now + lifetime,
        )
        return record, raw_token

    @classmethod
    def find_valid(cls, raw_token, purposes):
        """Return the matching unused, unexpired token, or None."""
        raw_token = (raw_token or "").strip()
        if not raw_token or len(raw_token) > 128:
            return None
        record = (
            cls.objects.select_related("user")
            .filter(token_hash=hash_token(raw_token), purpose__in=purposes)
            .first()
        )
        return record if record and record.is_valid else None
