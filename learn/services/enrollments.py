"""Joining, leaving, and reporting a student's learning problems to the instructor."""

from django.db import transaction
from django.utils import timezone

from learn.models import Enrollment, Event, Student
from learn.services import ServiceError, events, tokens
from learn.services.courses import enrollment_for_course, get_accessible_lesson


@transaction.atomic
def join(course, *, name: str, email: str, existing_student: Student | None = None) -> tuple[Enrollment, str]:
    """Create (or reuse) a student and enroll them. Returns (enrollment, raw_token)."""
    student = existing_student
    if student is None:
        student = Student.objects.create(name=name.strip(), email=email.strip().lower())
    else:
        student.name, student.email = name.strip(), email.strip().lower()
        student.save(update_fields=["name", "email"])

    if Enrollment.objects.filter(student=student, course=course).exists():
        raise ServiceError("You have already joined this class.")

    enrollment = Enrollment(student=student, course=course, consent_at=timezone.now())
    raw = tokens.assign_new_token(enrollment, save=False)
    enrollment.save()
    return enrollment, raw


@transaction.atomic
def leave(enrollment) -> None:
    """Leave a class and delete everything recorded for it (PRD §11)."""
    student = enrollment.student
    enrollment.delete()  # cascades attempts, answers, events, tool-call logs
    if not student.enrollments.exists():
        student.delete()


PROBLEM_CATEGORIES = {c for c, _ in Event.CATEGORY_CHOICES}
SEVERITIES = {c for c, _ in Event.SEVERITY_CHOICES}


def report_problem(
    enrollment,
    *,
    lesson_id: int | None,
    concept: str,
    category: str = Event.CAT_CONCEPT,
    severity: str = Event.MEDIUM,
    note: str = "",
    client: str = "",
) -> dict:
    """Record a learning problem so the instructor can follow up with the student."""
    concept = (concept or "").strip()
    if not concept:
        raise ServiceError("Give the topic of the problem (a few words), then call report_problem again.")
    category = (category or Event.CAT_CONCEPT).strip().lower()
    if category not in PROBLEM_CATEGORIES:
        raise ServiceError(f"category must be one of: {', '.join(sorted(PROBLEM_CATEGORIES))}.")
    severity = (severity or Event.MEDIUM).strip().lower()
    if severity not in SEVERITIES:
        raise ServiceError("severity must be low, medium or high.")
    lesson = None
    target = enrollment
    if lesson_id:
        lesson = get_accessible_lesson(enrollment, lesson_id)
        target = enrollment_for_course(enrollment, lesson.course_id)
    events.record(
        target, Event.PROBLEM, lesson=lesson, concept=concept, note=note, category=category, severity=severity,
        client=client,
    )
    return {
        "recorded": True,
        "concept": concept,
        "category": category,
        "lesson": lesson.title if lesson else None,
        "instructions": "Tell the student their instructor has been notified, then help them a different way.",
    }
