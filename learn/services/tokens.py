"""Personal student tokens for the MCP URL (PRD §10).

Only the SHA-256 hash is stored. The raw token is shown to the student once.
"""

import hashlib
import re
import secrets

from django.utils import timezone

TOKEN_BYTES = 32
# token_urlsafe(32) yields 43 characters from [A-Za-z0-9_-].
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def looks_like_token(raw: str) -> bool:
    return bool(raw) and bool(TOKEN_RE.match(raw))


def assign_new_token(enrollment, *, save: bool = True) -> str:
    """Give the enrollment a fresh token, invalidating the old one. Returns the raw token."""
    raw = generate_token()
    enrollment.token_hash = hash_token(raw)
    enrollment.token_hint = raw[-4:]
    if enrollment.pk:
        enrollment.token_rotated_at = timezone.now()
    if save:
        enrollment.save()
    return raw


def resolve(raw: str):
    """Return the Enrollment for a raw token, or None if unknown or revoked."""
    from learn.models import Enrollment

    if not looks_like_token(raw):
        return None
    return (
        Enrollment.objects.select_related("student", "course")
        .filter(token_hash=hash_token(raw))
        .first()
    )


def extract_token_from_url(value: str) -> str | None:
    """Pull the token out of a pasted personal MCP URL (or accept a bare token)."""
    value = (value or "").strip()
    match = re.search(r"/s/([A-Za-z0-9_-]+)/mcp", value)
    candidate = match.group(1) if match else value
    return candidate if looks_like_token(candidate) else None
