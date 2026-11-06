"""Django settings for learnmcp.

All deployment-specific values come from environment variables (see .env.example).
"""

import os
import sys
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = env_bool("DJANGO_DEBUG", False)
TESTING = "pytest" in sys.modules
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    # Development/test fallback only. The Docker entrypoint refuses to start without a real key.
    SECRET_KEY = "dev-insecure-secret-key-change-me"

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")
# Hostnames used inside the compose network (the Next.js server fetches public class data from http://web:8000).
ALLOWED_HOSTS += [h for h in env_list("DJANGO_INTERNAL_HOSTS", "web") if h not in ALLOWED_HOSTS]
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")

# Public base URL used when building student MCP URLs and invite links,
# e.g. https://learnmcp.example.com. Falls back to the request host.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "learn.apps.LearnConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = None
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=int(os.environ.get("DB_CONN_MAX_AGE", "0")),
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG or TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/admin/login/"

# --- Security (production behind a TLS-terminating proxy) -------------------
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = env_bool("DJANGO_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SECURE_SSL_REDIRECT = env_bool("DJANGO_SSL_REDIRECT", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 90  # students stay "signed in" to /me for 90 days

# --- learnmcp-specific settings ----------------------------------------------
# Requests per minute allowed per student token on the MCP endpoint.
MCP_RATE_LIMIT_PER_MINUTE = int(os.environ.get("MCP_RATE_LIMIT_PER_MINUTE", "60"))
# Host headers accepted by the MCP endpoint (DNS-rebinding protection).
# Empty = protection disabled (fine behind a reverse proxy that validates hosts).
MCP_ALLOWED_HOSTS = env_list("MCP_ALLOWED_HOSTS", "")
INACTIVE_AFTER_DAYS = int(os.environ.get("INACTIVE_AFTER_DAYS", "7"))

# --- Email (verification + inactivity reminders) -----------------------------
EMAIL_HOST = os.environ.get("SMTP_HOST", "")
EMAIL_PORT = int(os.environ.get("SMTP_PORT", "587") or 587)
EMAIL_HOST_USER = os.environ.get("SMTP_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_USE_SSL = env_bool("SMTP_USE_SSL", False)
EMAIL_USE_TLS = env_bool("SMTP_USE_TLS", True) and not EMAIL_USE_SSL
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = (
    os.environ.get("DEFAULT_FROM_EMAIL") or os.environ.get("SMTP_FROM") or EMAIL_HOST_USER or "webmaster@localhost"
)
# Without SMTP settings, emails are printed to the log instead of being sent.
EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
# How long an email-verification link stays valid.
EMAIL_VERIFY_MAX_AGE_DAYS = int(os.environ.get("EMAIL_VERIFY_MAX_AGE_DAYS", "3"))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": os.environ.get("LOG_LEVEL", "INFO")},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

# Hosts allowed as OAuth redirect targets for the auto-approving OAuth shim (learn/oauth.py).
OAUTH_REDIRECT_HOSTS = [
    h.strip().lower()
    for h in os.environ.get("OAUTH_REDIRECT_HOSTS", "claude.ai,claude.com,anthropic.com,chatgpt.com,openai.com").split(",")
    if h.strip()
]

CSRF_FAILURE_VIEW = "learn.api.csrf_failure"
