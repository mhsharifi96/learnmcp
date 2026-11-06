"""Class cover images: an uploaded photo, or an automatic cover themed by the class subject."""

from django.utils import timezone

from learn.services import ServiceError

MAX_BYTES = 3 * 1024 * 1024

# First match wins; checked against the lower-cased title and description.
THEMES: list[tuple[str, tuple[str, ...]]] = [
    ("code", ("python", "پایتون", "برنامه‌نویسی", "برنامه نویسی", "programming", "javascript", "coding")),
    ("math", ("ریاضی", "جبر", "هندسه", "math", "algebra", "geometry", "calculus")),
    ("career", ("مصاحبه", "شغل", "رزومه", "interview", "career", "resume")),
    ("finance", ("مالی", "پول", "سرمایه", "finance", "money", "budget", "invest")),
    ("science", ("زیست", "شیمی", "فیزیک", "biology", "chemistry", "physics", "science")),
    ("language", ("english", "انگلیسی", "ielts", "آیلتس", "grammar", "vocabulary", "زبان", "pronunciation")),
]
DEFAULT_THEME = "general"


def theme(course) -> str:
    text = f"{course.title} {course.description}".lower()
    for name, words in THEMES:
        if any(w in text for w in words):
            return name
    return DEFAULT_THEME


def _sniff(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def set_image(course, data: bytes) -> None:
    if not data:
        raise ServiceError("Choose an image file.")
    if len(data) > MAX_BYTES:
        raise ServiceError("The image is too large. Use a JPG, PNG or WebP under 3 MB.")
    content_type = _sniff(data)
    if content_type is None:
        raise ServiceError("Use a JPG, PNG or WebP image.")
    course.image_data = data
    course.image_type = content_type
    course.image_updated_at = timezone.now()
    course.save(update_fields=["image_data", "image_type", "image_updated_at"])


def clear_image(course) -> None:
    course.image_data = None
    course.image_type = ""
    course.image_updated_at = None
    course.save(update_fields=["image_data", "image_type", "image_updated_at"])


def payload(course) -> dict:
    """What pages need: the uploaded image URL (or None) and the automatic cover theme."""
    image = None
    if course.image_updated_at:
        image = f"/api/classes/{course.join_code}/image?v={int(course.image_updated_at.timestamp())}"
    return {"image": image, "theme": theme(course)}
