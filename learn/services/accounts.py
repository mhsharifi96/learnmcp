"""Student accounts: sign up with email + password, verify the email, log in."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import signing
from django.db import transaction
from django.utils import timezone

from learn.models import Student
from learn.services import ServiceError, emails

VERIFY_SALT = "learnmcp.verify-email"


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def email_taken(email: str) -> bool:
    User = get_user_model()
    return User.objects.filter(username__iexact=email).exists() or User.objects.filter(email__iexact=email).exists()


@transaction.atomic
def create_student_account(
    *, name: str, email: str, password: str, lang: str = "fa", claim: Student | None = None
) -> Student:
    """Create a login for a student. `claim` attaches an existing account-less student (joined before)."""
    email = normalize_email(email)
    if email_taken(email):
        raise ServiceError("An account with this email already exists. Log in instead.")
    user = get_user_model().objects.create_user(username=email, email=email, password=password)
    lang = lang if lang in ("fa", "en") else "fa"
    if claim is not None and claim.user_id is None:
        student = claim
        if normalize_email(student.email) != email:
            student.email_verified_at = None
        student.user, student.name, student.email, student.lang = user, name.strip(), email, lang
        student.save()
    else:
        student = Student.objects.create(user=user, name=name.strip(), email=email, lang=lang)
    return student


def verification_token(student: Student) -> str:
    return signing.dumps({"s": student.id, "e": normalize_email(student.email)}, salt=VERIFY_SALT)


def send_verification(student: Student, base_url: str) -> bool:
    link = f"{base_url}/verify-email/?token={verification_token(student)}"
    return emails.send(
        "verify", student.email, student.lang, name=student.name, link=link, days=settings.EMAIL_VERIFY_MAX_AGE_DAYS
    )


def verify(token: str) -> Student:
    try:
        data = signing.loads(token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFY_MAX_AGE_DAYS * 86400)
    except signing.SignatureExpired as exc:
        raise ServiceError("This link has expired. Log in and send a new one.") from exc
    except signing.BadSignature as exc:
        raise ServiceError("This link is not valid.") from exc
    student = Student.objects.filter(pk=data.get("s")).first()
    if student is None or normalize_email(student.email) != data.get("e"):
        raise ServiceError("This link is not valid.")
    if student.email_verified_at is None:
        student.email_verified_at = timezone.now()
        student.save(update_fields=["email_verified_at"])
    return student
