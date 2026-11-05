"""Read access to a student's classes and lessons.

A personal token belongs to one enrollment, but free Claude allows only ONE custom
connector, so the token gives access to every class the same student joined
(students are linked across classes only through the same browser session at join
time, never by unverified email).
"""

from django.db.models import Count, Prefetch, Q

from learn.models import Enrollment, Event, Lesson, Quiz, QuizAttempt
from learn.services import ServiceError, events, lesson_kinds

LESSON_NOT_STARTED = "not_started"
LESSON_STARTED = "started"
LESSON_QUIZ_DONE = "quiz_done"

BRIEF_RULES = (
    "The instructor wrote only a short lesson prompt (instructor_lesson_prompt), not the full lesson. "
    "First build a lesson plan from it yourself: 3-5 clear objectives, a simple explanation, worked examples "
    "and short practice tasks suited to the stated level. Briefly tell the student what the lesson will cover, "
    "then teach it. "
)

TEACHING_RULES = (
    "Teach this lesson conversationally, one idea at a time, and check understanding with short questions. "
    "Stay within the lesson content and objectives. "
    "If the student says they don't understand something, or keeps getting one concept wrong, "
    "call report_problem with that concept FIRST (category 'concept' or 'repeated_mistake'), then explain it another way. "
    "When the student is ready to be tested, call start_quiz with the quiz_id listed below. "
    "During a quiz follow the instructions start_quiz returns: for instructor-written quizzes ask ONE question "
    "at a time and send the reply unchanged to submit_answer (never judge it yourself); for AI-generated "
    "quizzes write the questions yourself and record each answer with record_ai_answer."
)


def student_enrollments(enrollment):
    return Enrollment.objects.filter(student_id=enrollment.student_id).select_related("course")


def enrollment_for_course(enrollment, course_id: int):
    if enrollment.course_id == course_id:
        return enrollment
    other = student_enrollments(enrollment).filter(course_id=course_id).first()
    if other is None:
        raise ServiceError("You are not enrolled in that class.")
    return other


def get_accessible_lesson(enrollment, lesson_id: int) -> Lesson:
    lesson = (
        Lesson.objects.select_related("course")
        .filter(pk=lesson_id, course__enrollments__student_id=enrollment.student_id)
        .first()
    )
    if lesson is None:
        raise ServiceError(
            f"Lesson {lesson_id} was not found in your classes. Call list_my_courses to see valid lesson ids."
        )
    return lesson


def lesson_statuses(enrollment_ids) -> dict[int, str]:
    started = set(
        Event.objects.filter(enrollment_id__in=enrollment_ids, type=Event.LESSON_STARTED, lesson__isnull=False)
        .values_list("lesson_id", flat=True)
    )
    finished_quiz_ids = set(
        QuizAttempt.objects.filter(enrollment_id__in=enrollment_ids, finished_at__isnull=False)
        .values_list("quiz_id", flat=True)
    )
    statuses = {}
    lessons = Lesson.objects.filter(course__enrollments__id__in=enrollment_ids).prefetch_related("quizzes")
    for lesson in lessons:
        quiz_ids = {q.id for q in lesson.quizzes.all()}
        if quiz_ids and quiz_ids <= finished_quiz_ids:
            statuses[lesson.id] = LESSON_QUIZ_DONE
        elif lesson.id in started:
            statuses[lesson.id] = LESSON_STARTED
        else:
            statuses[lesson.id] = LESSON_NOT_STARTED
    return statuses


def _quiz_summary(quiz, finished_scores: dict[int, float]) -> dict:
    data = {
        "quiz_id": quiz.id,
        "title": quiz.title,
        "questions": quiz.ai_question_count if quiz.is_ai else quiz.num_questions,
    }
    if quiz.is_ai:
        data["ai_generated"] = True
    if quiz.id in finished_scores:
        data["best_score_percent"] = round(finished_scores[quiz.id] * 100)
    return data


def list_courses(enrollment) -> dict:
    enrollments = list(student_enrollments(enrollment))
    ids = [e.id for e in enrollments]
    statuses = lesson_statuses(ids)

    finished_scores: dict[int, float] = {}
    for quiz_id, score in QuizAttempt.objects.filter(
        enrollment_id__in=ids, finished_at__isnull=False
    ).values_list("quiz_id", "score"):
        finished_scores[quiz_id] = max(finished_scores.get(quiz_id, 0.0), score or 0.0)


    quizzes_qs = Quiz.objects.annotate(num_questions=Count("questions", filter=Q(questions__attempt__isnull=True)))
    courses = []
    for enr in enrollments:
        course = enr.course
        lessons = (
            Lesson.objects.filter(course=course)
            .prefetch_related(Prefetch("quizzes", queryset=quizzes_qs))
            .order_by("order", "id")
        )
        course_quizzes = quizzes_qs.filter(course=course, lesson__isnull=True)
        courses.append(
            {
                "course_id": course.id,
                "title": course.title,
                "description": course.description,
                "lessons": [
                    {
                        "lesson_id": lesson.id,
                        "order": lesson.order,
                        "title": lesson.title,
                        "status": statuses.get(lesson.id, LESSON_NOT_STARTED),
                        "quizzes": [_quiz_summary(q, finished_scores) for q in lesson.quizzes.all()],
                    }
                    for lesson in lessons
                ],
                "class_quizzes": [_quiz_summary(q, finished_scores) for q in course_quizzes],
            }
        )
    return {
        "student_name": enrollment.student.name,
        "courses": courses,
        "hint": "Use get_lesson(lesson_id) to teach a lesson and start_quiz(quiz_id) to quiz the student.",
    }


def get_lesson(enrollment, lesson_id: int, *, client: str = "") -> dict:
    lesson = get_accessible_lesson(enrollment, lesson_id)
    target = enrollment_for_course(enrollment, lesson.course_id)
    events.record(target, Event.LESSON_STARTED, lesson=lesson, client=client)

    next_lesson = (
        Lesson.objects.filter(course_id=lesson.course_id, order__gt=lesson.order).order_by("order", "id").first()
    )
    return {
        "lesson_id": lesson.id,
        "course": lesson.course.title,
        "title": lesson.title,
        "lesson_type": lesson.kind,
        "objectives": lesson.objectives_list,
        "instructor_lesson_prompt": lesson.brief or None,
        "content": lesson.content or None,
        "instructor_teaching_notes": lesson.teaching_notes,
        "quizzes": [
            {"quiz_id": q.id, "title": q.title, "ai_generated": q.is_ai} for q in lesson.quizzes.all()
        ],
        "next_lesson": (
            {"lesson_id": next_lesson.id, "title": next_lesson.title} if next_lesson else None
        ),
        "how_to_teach": (BRIEF_RULES if not lesson.content.strip() else "")
        + (lesson_kinds.rules(lesson.kind) + " " if lesson_kinds.rules(lesson.kind) else "")
        + TEACHING_RULES,
    }
