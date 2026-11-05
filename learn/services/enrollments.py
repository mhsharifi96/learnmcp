"""Joining, leaving, and the "I'm stuck" signal."""

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


def report_stuck(enrollment, *, lesson_id: int | None, concept: str, note: str = "", client: str = "") -> dict:
    concept = (concept or "").strip()
    if not concept:
        raise ServiceError("Give the concept the student is stuck on (a few words), then call report_stuck again.")
    lesson = None
    target = enrollment
    if lesson_id:
        lesson = get_accessible_lesson(enrollment, lesson_id)
        target = enrollment_for_course(enrollment, lesson.course_id)
    events.record(target, Event.STUCK, lesson=lesson, concept=concept, note=note, client=client)
    return {
        "recorded": True,
        "concept": concept,
        "lesson": lesson.title if lesson else None,
        "instructions": "Tell the student their instructor has been notified, then explain the concept a different way.",
    }
