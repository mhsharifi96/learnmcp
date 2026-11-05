"""Progress for students (get_progress) and aggregates for the instructor dashboard."""

from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, Max, Q
from django.utils import timezone

from learn.models import Answer, Enrollment, Event, Lesson, Question, Quiz, QuizAttempt
from learn.services import events
from learn.services.courses import (
    LESSON_NOT_STARTED,
    LESSON_QUIZ_DONE,
    LESSON_STARTED,
    lesson_statuses,
    student_enrollments,
)


def _next_step(course, statuses, finished_quiz_ids) -> str:
    lessons = list(Lesson.objects.filter(course=course).prefetch_related("quizzes").order_by("order", "id"))
    for lesson in lessons:
        status = statuses.get(lesson.id, LESSON_NOT_STARTED)
        if status == LESSON_STARTED:
            pending = [q for q in lesson.quizzes.all() if q.id not in finished_quiz_ids]
            if pending:
                return f'Take the quiz "{pending[0].title}" (quiz_id={pending[0].id}) for lesson "{lesson.title}".'
        if status == LESSON_NOT_STARTED:
            return f'Start lesson {lesson.order}: "{lesson.title}" (lesson_id={lesson.id}).'
    for quiz in Quiz.objects.filter(course=course, lesson__isnull=True):
        if quiz.id not in finished_quiz_ids:
            return f'Take the class quiz "{quiz.title}" (quiz_id={quiz.id}).'
    return "Everything in this class is done. Review any concepts marked as stuck, or retake a quiz."


def student_progress(enrollment, *, client: str = "") -> dict:
    enrollments = list(student_enrollments(enrollment))
    ids = [e.id for e in enrollments]
    statuses = lesson_statuses(ids)
    finished = QuizAttempt.objects.filter(enrollment_id__in=ids, finished_at__isnull=False)
    finished_quiz_ids = set(finished.values_list("quiz_id", flat=True))

    courses = []
    for enr in enrollments:
        course = enr.course
        lesson_ids = list(Lesson.objects.filter(course=course).values_list("id", flat=True))
        course_attempts = finished.filter(enrollment=enr)
        avg = course_attempts.aggregate(a=Avg("score"))["a"]
        stuck = Counter(
            c.strip().lower()
            for c in Event.objects.filter(enrollment=enr, type=Event.STUCK).values_list("concept", flat=True)
            if c.strip()
        )
        courses.append(
            {
                "course_id": course.id,
                "title": course.title,
                "lessons_total": len(lesson_ids),
                "lessons_started": sum(1 for i in lesson_ids if statuses.get(i) in (LESSON_STARTED, LESSON_QUIZ_DONE)),
                "lessons_with_quiz_done": sum(1 for i in lesson_ids if statuses.get(i) == LESSON_QUIZ_DONE),
                "quizzes_finished": course_attempts.values("quiz_id").distinct().count(),
                "average_quiz_score_percent": None if avg is None else round(avg * 100),
                "stuck_concepts": [c for c, _ in stuck.most_common(5)],
                "suggested_next_step": _next_step(course, statuses, finished_quiz_ids),
            }
        )
    events.record(enrollment, Event.PROGRESS_VIEWED, client=client)
    return {"student_name": enrollment.student.name, "courses": courses}


# --------------------------------------------------------------------------- dashboard


def course_dashboard(course) -> dict:
    inactive_after = timedelta(days=settings.INACTIVE_AFTER_DAYS)
    now = timezone.now()

    enrollments = (
        Enrollment.objects.filter(course=course)
        .select_related("student")
        .annotate(
            avg_score=Avg("attempts__score", filter=Q(attempts__finished_at__isnull=False)),
            stuck_count=Count("events", filter=Q(events__type=Event.STUCK), distinct=True),
            quizzes_done=Count("attempts", filter=Q(attempts__finished_at__isnull=False), distinct=True),
            last_event=Max("events__created_at"),
        )
        .order_by("student__name")
    )
    students = []
    for enr in enrollments:
        last = max(filter(None, [enr.last_activity_at, enr.last_event]), default=None)
        students.append(
            {
                "enrollment": enr,
                "name": enr.student.name,
                "email": enr.student.email,
                "joined_at": enr.joined_at,
                "last_activity": last,
                "inactive": last is None or (now - last) > inactive_after,
                "avg_score_percent": None if enr.avg_score is None else round(enr.avg_score * 100),
                "quizzes_done": enr.quizzes_done,
                "stuck_count": enr.stuck_count,
            }
        )

    question_stats = (
        Question.objects.filter(quiz__course=course, attempt__isnull=True)
        .annotate(
            answered=Count("answers"),
            correct=Count("answers", filter=Q(answers__status=Answer.CORRECT)),
            incorrect=Count("answers", filter=Q(answers__status=Answer.INCORRECT)),
            review=Count("answers", filter=Q(answers__status=Answer.NEEDS_REVIEW)),
        )
        .select_related("quiz")
        .filter(answered__gt=0)
    )
    questions = []
    for q in question_stats:
        questions.append(
            {
                "question": q,
                "answered": q.answered,
                "correct": q.correct,
                "missed": q.incorrect,
                "needs_review": q.review,
                "correct_rate": round(100 * q.correct / q.answered) if q.answered else None,
            }
        )
    questions.sort(key=lambda r: (r["correct_rate"] if r["correct_rate"] is not None else 101, -r["answered"]))

    stuck_counter: Counter = Counter()
    stuck_examples: dict[str, list[str]] = {}
    for concept, note, name in Event.objects.filter(enrollment__course=course, type=Event.STUCK).values_list(
        "concept", "note", "enrollment__student__name"
    ):
        key = (concept or "(unspecified)").strip().lower()
        stuck_counter[key] += 1
        if note and len(stuck_examples.setdefault(key, [])) < 3:
            stuck_examples[key].append(f"{name}: {note}")

    stuck = [
        {"concept": c, "count": n, "notes": stuck_examples.get(c, [])} for c, n in stuck_counter.most_common(15)
    ]

    return {
        "students": students,
        "student_count": len(students),
        "inactive_count": sum(1 for s in students if s["inactive"]),
        "inactive_days": settings.INACTIVE_AFTER_DAYS,
        "questions": questions[:15],
        "stuck": stuck,
        "needs_review_count": Answer.objects.filter(
            attempt__enrollment__course=course, status=Answer.NEEDS_REVIEW
        ).count(),
        "finished_attempts": QuizAttempt.objects.filter(enrollment__course=course, finished_at__isnull=False).count(),
    }
