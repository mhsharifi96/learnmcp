"""Progress for students (get_progress) and aggregates for the instructor dashboard."""

from collections import Counter
from datetime import timedelta

from django.conf import settings
from django.db.models import Avg, Count, F, Max, Prefetch, Q
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
    lessons = list(
        Lesson.objects.published().filter(course=course)
        .prefetch_related(Prefetch("quizzes", queryset=Quiz.objects.published()))
        .order_by("order", "id")
    )
    for lesson in lessons:
        status = statuses.get(lesson.id, LESSON_NOT_STARTED)
        if status == LESSON_STARTED:
            pending = [q for q in lesson.quizzes.all() if q.id not in finished_quiz_ids]
            if pending:
                return f'Take the quiz "{pending[0].title}" (quiz_id={pending[0].id}) for lesson "{lesson.title}".'
        if status == LESSON_NOT_STARTED:
            return f'Start lesson {lesson.order}: "{lesson.title}" (lesson_id={lesson.id}).'
    for quiz in Quiz.objects.published().filter(course=course, lesson__isnull=True):
        if quiz.id not in finished_quiz_ids:
            return f'Take the class quiz "{quiz.title}" (quiz_id={quiz.id}).'
    return "Everything in this class is done. Review the concepts listed in open_problems, or retake a quiz."


def student_progress(enrollment, *, client: str = "") -> dict:
    enrollments = list(student_enrollments(enrollment))
    ids = [e.id for e in enrollments]
    statuses = lesson_statuses(ids)
    finished = QuizAttempt.objects.filter(enrollment_id__in=ids, finished_at__isnull=False)
    finished_quiz_ids = set(finished.values_list("quiz_id", flat=True))

    courses = []
    for enr in enrollments:
        course = enr.course
        lesson_ids = list(Lesson.objects.published().filter(course=course).values_list("id", flat=True))
        course_attempts = finished.filter(enrollment=enr)
        avg = course_attempts.aggregate(a=Avg("score"))["a"]
        problems = Counter(
            c.strip().lower()
            for c in Event.objects.filter(
                enrollment=enr, type=Event.PROBLEM, resolved_at__isnull=True
            ).values_list("concept", flat=True)
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
                "open_problems": [c for c, _ in problems.most_common(5)],
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
            problem_count=Count(
                "events", filter=Q(events__type=Event.PROBLEM, events__resolved_at__isnull=True), distinct=True
            ),
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
                "problem_count": enr.problem_count,
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

    # Weak concepts: open problem reports plus concepts of wrongly answered questions.
    weak: Counter = Counter()
    weak_students: dict[str, set] = {}
    for concept, name in Event.objects.filter(
        enrollment__course=course, type=Event.PROBLEM, resolved_at__isnull=True
    ).values_list("concept", "enrollment__student__name"):
        for c in (concept or "").split(","):
            key = c.strip().lower()
            if key:
                weak[key] += 1
                weak_students.setdefault(key, set()).add(name)
    for concept, name in Answer.objects.filter(
        attempt__enrollment__course=course, status=Answer.INCORRECT
    ).exclude(question__concept="").values_list("question__concept", "attempt__enrollment__student__name"):
        key = concept.strip().lower()
        weak[key] += 1
        weak_students.setdefault(key, set()).add(name)
    weak_concepts = [
        {"concept": c, "count": n, "students": sorted(weak_students.get(c, set()))} for c, n in weak.most_common(12)
    ]

    problems = list(
        Event.objects.filter(enrollment__course=course, type=Event.PROBLEM)
        .select_related("enrollment__student", "lesson", "attempt__quiz")
        .order_by(F("resolved_at").asc(nulls_first=True), "-created_at")[:60]
    )

    return {
        "students": students,
        "student_count": len(students),
        "inactive_count": sum(1 for s in students if s["inactive"]),
        "inactive_days": settings.INACTIVE_AFTER_DAYS,
        "questions": questions[:15],
        "weak_concepts": weak_concepts,
        "problems": problems,
        "open_problem_count": Event.objects.filter(
            enrollment__course=course, type=Event.PROBLEM, resolved_at__isnull=True
        ).count(),
        "needs_review_count": Answer.objects.filter(
            attempt__enrollment__course=course, status=Answer.NEEDS_REVIEW
        ).count(),
        "finished_attempts": QuizAttempt.objects.filter(enrollment__course=course, finished_at__isnull=False).count(),
    }
