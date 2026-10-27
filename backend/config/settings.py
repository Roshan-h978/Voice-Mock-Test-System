"""
Django settings for the Voice Mock Test System API.

Every secret and environment-specific value is read from backend/.env
(copy backend/.env.example to backend/.env). Nothing secret is stored in code.
"""

import sys
from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# ---------------------------------------------------------------------------
# Paths and environment
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend

env = environ.Env()
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)
elif (BASE_DIR.parent / ".env").exists():  # older layout: .env next to the backend folder
    ENV_FILE = BASE_DIR.parent / ".env"
    environ.Env.read_env(ENV_FILE)

TESTING = len(sys.argv) > 1 and sys.argv[1] == "test"

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env.bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="")
if not DEBUG and (not SECRET_KEY or SECRET_KEY.startswith("change-me")):
    if not ENV_FILE.exists():
        raise ImproperlyConfigured(
            f"No settings file found at {ENV_FILE}. Copy backend/.env.example to backend/.env and start again."
        )
    raise ImproperlyConfigured(
        "Set a real DJANGO_SECRET_KEY in backend/.env before running with DJANGO_DEBUG=False."
    )
SECRET_KEY = SECRET_KEY or "dev-only-insecure-key-set-DJANGO_SECRET_KEY-in-backend-env"

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.tests_manager",
    "apps.attempts",
    "apps.evaluation",
    "apps.notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database: SQLite for local development, PostgreSQL (Supabase) via DATABASE_URL
# ---------------------------------------------------------------------------
DATABASE_URL = env("DATABASE_URL", default="")
if DATABASE_URL:
    DATABASES = {"default": env.db_url_config(DATABASE_URL)}
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE", default=60)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Language and time
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", default="Asia/Kathmandu")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files and uploaded recordings
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGE_BACKEND = env("STORAGE_BACKEND", default="local").lower()
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
if STORAGE_BACKEND == "s3":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET_NAME"),
            "endpoint_url": env("S3_ENDPOINT_URL", default=None),
            "region_name": env("S3_REGION_NAME", default=None),
            "access_key": env("S3_ACCESS_KEY_ID"),
            "secret_key": env("S3_SECRET_ACCESS_KEY"),
            "addressing_style": "path",
            "signature_version": "s3v4",
            "default_acl": None,
            "file_overwrite": False,
            "querystring_auth": True,  # private bucket, signed playback links
            "querystring_expire": 3600,
        },
    }

# ---------------------------------------------------------------------------
# Django REST Framework and JWT
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "EXCEPTION_HANDLER": "apps.common.utils.api_exception_handler",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="600/min"),
        "auth": env("THROTTLE_AUTH", default="30/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------------------------
# Frontend, CORS and CSRF
# ---------------------------------------------------------------------------
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:5173").rstrip("/")
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[FRONTEND_URL])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[FRONTEND_URL])

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Voice Mock Test <no-reply@example.com>")

# ---------------------------------------------------------------------------
# Voice Mock Test: accounts and uploads
# ---------------------------------------------------------------------------
ALLOW_PUBLIC_REGISTRATION = env.bool("ALLOW_PUBLIC_REGISTRATION", default=True)
INVITE_VALID_DAYS = env.int("INVITE_VALID_DAYS", default=7)
PASSWORD_RESET_VALID_HOURS = env.int("PASSWORD_RESET_VALID_HOURS", default=1)
MAX_AUDIO_UPLOAD_MB = env.int("MAX_AUDIO_UPLOAD_MB", default=15)

# ---------------------------------------------------------------------------
# Voice Mock Test: first admin account (created by the database migration)
# ---------------------------------------------------------------------------
DEFAULT_ADMIN_EMAIL = env("DEFAULT_ADMIN_EMAIL", default="admin@example.com").strip().lower()
DEFAULT_ADMIN_PASSWORD = env("DEFAULT_ADMIN_PASSWORD", default="admin123")
DEFAULT_ADMIN_NAME = env("DEFAULT_ADMIN_NAME", default="Admin")

# ---------------------------------------------------------------------------
# Voice Mock Test: Google sign-in (Google Identity Services)
# ---------------------------------------------------------------------------
# Leave empty to hide the "Continue with Google" button.
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="").strip()
GOOGLE_CERTS_URL = env("GOOGLE_CERTS_URL", default="https://www.googleapis.com/oauth2/v1/certs")

# ---------------------------------------------------------------------------
# Voice Mock Test: speech evaluation (OpenAI speech-to-text + Anthropic Claude)
# ---------------------------------------------------------------------------
EVALUATION_DEMO_MODE = env.bool("EVALUATION_DEMO_MODE", default=False)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_BASE_URL = env("OPENAI_BASE_URL", default="https://api.openai.com/v1").rstrip("/")
TRANSCRIBE_MODEL = env("TRANSCRIBE_MODEL", default="whisper-1")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default="")
ANTHROPIC_BASE_URL = env("ANTHROPIC_BASE_URL", default="https://api.anthropic.com").rstrip("/")
SCORING_MODEL = env("SCORING_MODEL", default="claude-haiku-5-5")
AI_REQUEST_TIMEOUT = env.int("AI_REQUEST_TIMEOUT", default=60)

SCORING = {
    "WEIGHTS": {
        "fluency": env.int("SCORE_WEIGHT_FLUENCY", default=40),
        "pronunciation": env.int("SCORE_WEIGHT_PRONUNCIATION", default=30),
        "grammar": env.int("SCORE_WEIGHT_GRAMMAR", default=30),
    },
    "REVIEW_THRESHOLD": env.int("REVIEW_THRESHOLD", default=65),
    "MIN_WORDS": 15,
    "MIN_CLARITY": 50,
    "MIN_RELEVANCE": 40,
    "IDEAL_WPM_MIN": 100,
    "IDEAL_WPM_MAX": 160,
    "LONG_PAUSE_SECONDS": 1.5,
}

# ---------------------------------------------------------------------------
# Voice Mock Test: n8n automation
# ---------------------------------------------------------------------------
AUTOMATION_API_KEY = env("AUTOMATION_API_KEY", default="")
EMAIL_DELIVERY = env("EMAIL_DELIVERY", default="django").lower()  # "django" or "n8n"
N8N_WEBHOOK_BASE_URL = env("N8N_WEBHOOK_BASE_URL", default="http://localhost:5678/webhook").rstrip("/")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "apps": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO"), "propagate": False},
    },
}

# Keep "python manage.py test" output readable: errors that tests trigger on purpose aren't printed.
if TESTING:
    LOGGING["handlers"]["console"]["level"] = "CRITICAL"
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast hashing for tests only

# ---------------------------------------------------------------------------
# Production security (applies when DJANGO_DEBUG=False)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=0)
