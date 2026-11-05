"""JSON API for the Next.js frontend (same origin, Django session + CSRF cookie).

Student endpoints reuse the anonymous-session model of the server-rendered pages: the
browser session remembers which enrollments belong to this visitor.

Instructor endpoints (/api/teach/...) require a logged-in staff user and are scoped to the
instructor's own classes (superusers see everything), mirroring the admin scoping.
"""

import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from learn import views as pages
from learn.apps import ensure_instructors_group
from learn.forms import InstructorSignupForm, JoinForm
from learn.models import (
    Answer,
    Course,
    Enrollment,
    Event,
    Instructor,
    Lesson,
    Question,
    Quiz,
    QuizAttempt,
    Student,
    ToolCall,
)
from learn.services import ServiceError, enrollments, grading, progress, quizzes, tokens


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400, errors: dict | None = None):
        super().__init__(message)
        self.status = status
        self.errors = errors or {}


def _body(request) -> dict:
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except ValueError as exc:
        raise ApiError("Body must be JSON.") from exc
    if not isinstance(data, dict):
        raise ApiError("Body must be a JSON object.")
    return data


def api(methods=("GET",), teach=False):
    def deco(fn):
        @wraps(fn)
        def wrapper(request, *args, **kwargs):
            if request.method not in methods:
                return JsonResponse({"error": "Method not allowed."}, status=405)
            try:
                if teach:
                    if not (request.user.is_authenticated and request.user.is_staff):
                        raise ApiError("Please log in as an instructor.", 401)
                result = fn(request, *args, **kwargs)
            except ApiError as exc:
                return JsonResponse({"error": str(exc), "errors": exc.errors}, status=exc.status)
            except ServiceError as exc:
                return JsonResponse({"error": str(exc), "errors": {}}, status=400)
            except ValidationError as exc:
                errors = {k: [str(m) for m in v] for k, v in getattr(exc, "message_dict", {"__all__": exc.messages}).items()}
                return JsonResponse({"error": "Please fix the highlighted fields.", "errors": errors}, status=400)
            if isinstance(result, JsonResponse):
                return result
            return JsonResponse(result if result is not None else {"ok": True}, safe=False)

        return wrapper

    return deco


def _form_errors(form) -> ApiError:
    return ApiError(
        "Please fix the highlighted fields.",
        errors={k: [str(m) for m in v] for k, v in form.errors.items()},
    )


def _dt(value):
    return value.isoformat() if value else None


# =========================================================================== session / auth


@ensure_csrf_cookie
@api()
def csrf(request):
    return {"ok": True}


def _user_payload(user) -> dict | None:
    if not (user.is_authenticated and user.is_staff):
        return None
    inst = getattr(user, "instructor", None)
    return {
        "username": user.get_username(),
        "display_name": inst.display_name if inst else user.get_username(),
        "is_superuser": user.is_superuser,
    }


@api()
def whoami(request):
    return {"user": _user_payload(request.user)}


@api(methods=("POST",))
def login_view(request):
    data = _body(request)
    user = authenticate(request, username=data.get("username", ""), password=data.get("password", ""))
    if user is None or not user.is_staff:
        raise ApiError("Wrong username or password.", 400)
    login(request, user)
    return {"user": _user_payload(user)}


@api(methods=("POST",))
def logout_view(request):
    logout(request)
    return {"ok": True}


@api(methods=("POST",))
def signup(request):
    data = _body(request)
    form = InstructorSignupForm(
        {
            "username": data.get("username", ""),
            "email": data.get("email", ""),
            "display_name": data.get("display_name", ""),
            "password1": data.get("password1", ""),
            "password2": data.get("password2", ""),
        }
    )
    if not form.is_valid():
        raise _form_errors(form)
    with transaction.atomic():
        user = form.save(commit=False)
        user.email = form.cleaned_data["email"]
        user.is_staff = True
        user.save()
        user.groups.add(ensure_instructors_group())
        Instructor.objects.create(user=user, display_name=form.cleaned_data["display_name"])
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return {"user": _user_payload(user)}


# =========================================================================== students


@api()
def class_info(request, code: str):
    course = Course.objects.select_related("instructor").filter(join_code=code.strip().upper()).first()
    if course is None:
        raise ApiError("No class with this code. Check it with your instructor.", 404)
    student = None
    sid = request.session.get(pages.SESSION_STUDENT)
    if sid:
        student = Student.objects.filter(pk=sid).first()
    already = bool(student and Enrollment.objects.filter(student=student, course=course).exists())
    return {
        "code": course.join_code,
        "title": course.title,
        "description": course.description,
        "instructor": course.instructor.display_name,
        "linked": student is not None,
        "already_joined": already,
        "student": {"name": student.name, "email": student.email} if student else None,
    }


@api(methods=("POST",))
def join_class(request, code: str):
    course = Course.objects.filter(join_code=code.strip().upper()).first()
    if course is None:
        raise ApiError("No class with this code.", 404)
    existing = None
    sid = request.session.get(pages.SESSION_STUDENT)
    if sid:
        existing = Student.objects.filter(pk=sid).first()
    data = _body(request)
    form = JoinForm(
        {
            "name": data.get("name", ""),
            "email": data.get("email", ""),
            "consent": bool(data.get("consent")),
        }
    )
    if not form.is_valid():
        raise _form_errors(form)
    enrollment, raw = enrollments.join(
        course, name=form.cleaned_data["name"], email=form.cleaned_data["email"], existing_student=existing
    )
    pages._remember_enrollment(request, enrollment)
    pages._stash_new_token(request, enrollment.id, raw)
    return {"enrollment_id": enrollment.id}


def _my_enrollment(request, enrollment_id: int) -> Enrollment:
    if enrollment_id not in pages._session_enrollment_ids(request):
        raise ApiError("Not found.", 404)
    enr = Enrollment.objects.select_related("student", "course", "course__instructor").filter(pk=enrollment_id).first()
    if enr is None:
        raise ApiError("Not found.", 404)
    return enr


@api()
def connect_info(request, enrollment_id: int):
    enr = _my_enrollment(request, enrollment_id)
    raw = pages._pop_new_token(request, enr.id)
    return {
        "enrollment_id": enr.id,
        "course": enr.course.title,
        "mcp_url": pages.mcp_url(request, raw) if raw else None,
        "token_hint": enr.token_hint,
        "other_classes": Enrollment.objects.filter(student=enr.student).exclude(pk=enr.pk).count(),
    }


@api(methods=("POST",))
def regenerate(request, enrollment_id: int):
    enr = _my_enrollment(request, enrollment_id)
    raw = tokens.assign_new_token(enr)
    pages._stash_new_token(request, enr.id, raw)
    return {"ok": True}


@api(methods=("POST",))
def leave(request, enrollment_id: int):
    enr = _my_enrollment(request, enrollment_id)
    enrollments.leave(enr)
    request.session[pages.SESSION_ENROLLMENTS] = [
        i for i in pages._session_enrollment_ids(request) if i != enrollment_id
    ]
    if not Student.objects.filter(pk=request.session.get(pages.SESSION_STUDENT)).exists():
        request.session.pop(pages.SESSION_STUDENT, None)
    return {"ok": True}


def _answer_payload(a: Answer) -> dict:
    return {
        "id": a.id,
        "question": a.question.prompt,
        "answer": a.raw_answer,
        "status": a.status,
        "answered_at": _dt(a.answered_at),
    }


def _attempt_payload(attempt: QuizAttempt, with_expected: bool = False) -> dict:
    answers = []
    for a in sorted(attempt.answers.all(), key=lambda a: (a.question.order, a.question_id)):
        item = _answer_payload(a)
        if with_expected:
            item["expected"] = grading.display_correct_answer(a.question)
            item["explanation"] = a.question.explanation
            item["concept"] = a.question.concept
            item["ai_generated"] = a.question.attempt_id is not None
        answers.append(item)
    statuses = [a["status"] for a in answers]
    total = attempt.quiz.ai_question_count if attempt.quiz.is_ai else None
    return {
        "id": attempt.id,
        "quiz": attempt.quiz.title,
        "lesson": attempt.quiz.lesson.title if attempt.quiz.lesson else None,
        "ai_generated": attempt.quiz.is_ai,
        "started_at": _dt(attempt.started_at),
        "finished_at": _dt(attempt.finished_at),
        "score_percent": attempt.score_percent,
        "correct": statuses.count(Answer.CORRECT),
        "incorrect": statuses.count(Answer.INCORRECT),
        "needs_review": statuses.count(Answer.NEEDS_REVIEW),
        "total": total or len(answers),
        "summary": attempt.summary,
        "weak_concepts": attempt.weak_concepts_json,
        "answers": answers,
    }


def _event_payload(ev: Event) -> dict:
    return {
        "type": ev.type,
        "label": ev.get_type_display(),
        "lesson": ev.lesson.title if ev.lesson else None,
        "concept": ev.concept,
        "note": ev.note,
        "category": ev.category,
        "client": ev.client,
        "created_at": _dt(ev.created_at),
    }


def _problem_payload(ev: Event) -> dict:
    return {
        "id": ev.id,
        "enrollment_id": ev.enrollment_id,
        "student": ev.enrollment.student.name,
        "category": ev.category or Event.CAT_OTHER,
        "severity": ev.severity or Event.MEDIUM,
        "concept": ev.concept,
        "note": ev.note,
        "lesson": ev.lesson.title if ev.lesson else None,
        "quiz": ev.attempt.quiz.title if ev.attempt_id and ev.attempt else None,
        "attempt_id": ev.attempt_id,
        "created_at": _dt(ev.created_at),
        "resolved_at": _dt(ev.resolved_at),
        "instructor_note": ev.instructor_note,
    }


@api()
def my_data(request):
    ids = pages._session_enrollment_ids(request)
    found = list(
        Enrollment.objects.filter(pk__in=ids)
        .select_related("student", "course", "course__instructor")
        .prefetch_related("events__lesson", "attempts__quiz", "attempts__answers__question")
    )
    request.session[pages.SESSION_ENROLLMENTS] = [e.id for e in found]
    return {
        "enrollments": [
            {
                "id": e.id,
                "course": e.course.title,
                "course_code": e.course.join_code,
                "instructor": e.course.instructor.display_name,
                "student": {"name": e.student.name, "email": e.student.email},
                "joined_at": _dt(e.joined_at),
                "consent_at": _dt(e.consent_at),
                "token_hint": e.token_hint,
                "attempts": [_attempt_payload(a) for a in e.attempts.all()],
                "events": [_event_payload(ev) for ev in e.events.all()],
            }
            for e in found
        ]
    }


@api(methods=("POST",))
def restore(request):
    raw = tokens.extract_token_from_url(str(_body(request).get("url", "")))
    enr = tokens.resolve(raw) if raw else None
    if enr is None:
        raise ApiError("This URL is not valid or was regenerated.", errors={"url": ["Not valid."]})
    for e in Enrollment.objects.filter(student=enr.student):
        pages._remember_enrollment(request, e)
    return {"ok": True}


# =========================================================================== instructors


def _instructor(request) -> Instructor | None:
    return getattr(request.user, "instructor", None)


def _courses(request):
    qs = Course.objects.select_related("instructor")
    if request.user.is_superuser:
        return qs
    inst = _instructor(request)
    return qs.filter(instructor=inst) if inst else qs.none()


def _course(request, course_id: int) -> Course:
    course = _courses(request).filter(pk=course_id).first()
    if course is None:
        raise ApiError("Class not found.", 404)
    return course


def _lesson(request, lesson_id: int) -> Lesson:
    lesson = Lesson.objects.filter(pk=lesson_id, course__in=_courses(request)).first()
    if lesson is None:
        raise ApiError("Lesson not found.", 404)
    return lesson


def _quiz(request, quiz_id: int) -> Quiz:
    quiz = Quiz.objects.filter(pk=quiz_id, course__in=_courses(request)).select_related("lesson").first()
    if quiz is None:
        raise ApiError("Quiz not found.", 404)
    return quiz


def _question(request, question_id: int) -> Question:
    q = Question.objects.filter(pk=question_id, quiz__course__in=_courses(request), attempt__isnull=True).first()
    if q is None:
        raise ApiError("Question not found.", 404)
    return q


def _apply(obj, data: dict, fields: tuple[str, ...]):
    for f in fields:
        if f in data:
            setattr(obj, f, data[f])
    obj.full_clean()
    obj.save()
    return obj


def _lesson_payload(lesson: Lesson) -> dict:
    return {
        "id": lesson.id,
        "order": lesson.order,
        "title": lesson.title,
        "brief": lesson.brief,
        "objectives": lesson.objectives,
        "content": lesson.content,
        "teaching_notes": lesson.teaching_notes,
    }


def _question_payload(q: Question) -> dict:
    return {
        "id": q.id,
        "order": q.order,
        "type": q.type,
        "prompt": q.prompt,
        "options": q.options_json,
        "correct_answer": q.correct_answer,
        "accepted_answers": q.accepted_answers_json,
        "explanation": q.explanation,
        "concept": q.concept,
    }


def _quiz_payload(quiz: Quiz, with_questions: bool = False) -> dict:
    data = {
        "id": quiz.id,
        "title": quiz.title,
        "lesson_id": quiz.lesson_id,
        "lesson": quiz.lesson.title if quiz.lesson else None,
        "mode": quiz.mode,
        "prompt": quiz.prompt,
        "ai_question_count": quiz.ai_question_count,
        "question_count": quiz.ai_question_count if quiz.is_ai else quiz.manual_questions().count(),
    }
    if with_questions:
        data["questions"] = [_question_payload(q) for q in quiz.manual_questions().order_by("order", "id")]
    return data


def _course_summary(course: Course) -> dict:
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "join_code": course.join_code,
        "instructor": course.instructor.display_name,
        "students": getattr(course, "_students", None),
        "lessons": getattr(course, "_lessons", None),
        "created_at": _dt(course.created_at),
    }


@api(methods=("GET", "POST"), teach=True)
def teach_courses(request):
    if request.method == "POST":
        data = _body(request)
        inst = _instructor(request)
        if inst is None:
            inst, _ = Instructor.objects.get_or_create(
                user=request.user, defaults={"display_name": request.user.get_username()}
            )
        course = _apply(Course(instructor=inst), data, ("title", "description"))
        return JsonResponse(_course_summary(course), status=201)
    qs = _courses(request).annotate(
        _students=Count("enrollments", distinct=True), _lessons=Count("lessons", distinct=True)
    ).order_by("-created_at")
    return {"courses": [_course_summary(c) for c in qs]}


@api(methods=("GET", "PATCH", "DELETE"), teach=True)
def teach_course(request, course_id: int):
    course = _course(request, course_id)
    if request.method == "DELETE":
        course.delete()
        return {"ok": True}
    if request.method == "PATCH":
        _apply(course, _body(request), ("title", "description"))
    data = _course_summary(course)
    data["lessons"] = [_lesson_payload(lesson) for lesson in course.lessons.order_by("order", "id")]
    data["quizzes"] = [_quiz_payload(q) for q in course.quizzes.select_related("lesson")]
    data["student_count"] = course.enrollments.count()
    return data


@api(teach=True)
def teach_dashboard(request, course_id: int):
    course = _course(request, course_id)
    d = progress.course_dashboard(course)
    calls = ToolCall.objects.filter(enrollment__course=course)
    total = calls.count()
    ok = calls.filter(ok=True).count()
    return {
        "course": {"id": course.id, "title": course.title, "join_code": course.join_code},
        "student_count": d["student_count"],
        "inactive_count": d["inactive_count"],
        "inactive_days": d["inactive_days"],
        "finished_attempts": d["finished_attempts"],
        "needs_review_count": d["needs_review_count"],
        "tool_calls_total": total,
        "tool_calls_ok_percent": round(100 * ok / total) if total else None,
        "students": [
            {
                "enrollment_id": s["enrollment"].id,
                "name": s["name"],
                "email": s["email"],
                "last_activity": _dt(s["last_activity"]),
                "inactive": s["inactive"],
                "avg_score_percent": s["avg_score_percent"],
                "quizzes_done": s["quizzes_done"],
                "problem_count": s["problem_count"],
            }
            for s in d["students"]
        ],
        "questions": [
            {
                "prompt": r["question"].prompt,
                "quiz": r["question"].quiz.title,
                "concept": r["question"].concept,
                "answered": r["answered"],
                "correct_rate": r["correct_rate"],
                "needs_review": r["needs_review"],
            }
            for r in d["questions"]
        ],
        "weak_concepts": d["weak_concepts"],
        "problems": [_problem_payload(ev) for ev in d["problems"]],
        "open_problem_count": d["open_problem_count"],
    }


@api(methods=("POST",), teach=True)
def teach_lessons(request, course_id: int):
    course = _course(request, course_id)
    data = _body(request)
    data.setdefault("order", (course.lessons.order_by("-order").values_list("order", flat=True).first() or 0) + 1)
    lesson = _apply(Lesson(course=course), data, ("order", "title", "brief", "objectives", "content", "teaching_notes"))
    return JsonResponse(_lesson_payload(lesson), status=201)


@api(methods=("PATCH", "DELETE"), teach=True)
def teach_lesson(request, lesson_id: int):
    lesson = _lesson(request, lesson_id)
    if request.method == "DELETE":
        lesson.delete()
        return {"ok": True}
    return _lesson_payload(
        _apply(lesson, _body(request), ("order", "title", "brief", "objectives", "content", "teaching_notes"))
    )


QUIZ_FIELDS = ("title", "mode", "prompt", "ai_question_count")


def _set_quiz_lesson(request, quiz: Quiz, data: dict) -> None:
    if "lesson_id" in data:
        lid = data["lesson_id"]
        if lid in (None, ""):
            quiz.lesson = None
        else:
            lesson = Lesson.objects.filter(pk=lid, course_id=quiz.course_id).first()
            if lesson is None:
                raise ApiError("The lesson must belong to the same class.", errors={"lesson_id": ["Invalid lesson."]})
            quiz.lesson = lesson


@api(methods=("POST",), teach=True)
def teach_quizzes(request, course_id: int):
    course = _course(request, course_id)
    data = _body(request)
    quiz = Quiz(course=course)
    _set_quiz_lesson(request, quiz, data)
    _apply(quiz, data, QUIZ_FIELDS)
    return JsonResponse(_quiz_payload(quiz, with_questions=True), status=201)


@api(methods=("GET", "PATCH", "DELETE"), teach=True)
def teach_quiz(request, quiz_id: int):
    quiz = _quiz(request, quiz_id)
    if request.method == "DELETE":
        quiz.delete()
        return {"ok": True}
    if request.method == "PATCH":
        data = _body(request)
        _set_quiz_lesson(request, quiz, data)
        _apply(quiz, data, QUIZ_FIELDS)
    payload = _quiz_payload(quiz, with_questions=True)
    payload["course_id"] = quiz.course_id
    payload["lessons"] = [
        {"id": lesson.id, "title": lesson.title} for lesson in quiz.course.lessons.order_by("order", "id")
    ]
    return payload


def _question_from(data: dict, q: Question) -> Question:
    mapping = {
        "order": "order",
        "type": "type",
        "prompt": "prompt",
        "options": "options_json",
        "correct_answer": "correct_answer",
        "accepted_answers": "accepted_answers_json",
        "explanation": "explanation",
        "concept": "concept",
    }
    for src, dst in mapping.items():
        if src in data:
            value = data[src]
            if src in ("options", "accepted_answers"):
                value = [str(v).strip() for v in (value or []) if str(v).strip()]
            setattr(q, dst, value)
    q.full_clean()
    q.save()
    return q


@api(methods=("POST",), teach=True)
def teach_questions(request, quiz_id: int):
    quiz = _quiz(request, quiz_id)
    data = _body(request)
    data.setdefault(
        "order", (quiz.manual_questions().order_by("-order").values_list("order", flat=True).first() or 0) + 1
    )
    return JsonResponse(_question_payload(_question_from(data, Question(quiz=quiz))), status=201)


@api(methods=("PATCH", "DELETE"), teach=True)
def teach_question(request, question_id: int):
    q = _question(request, question_id)
    if request.method == "DELETE":
        q.delete()
        return {"ok": True}
    return _question_payload(_question_from(_body(request), q))


@api(teach=True)
def teach_student(request, enrollment_id: int):
    enr = (
        Enrollment.objects.filter(pk=enrollment_id, course__in=_courses(request))
        .select_related("student", "course")
        .prefetch_related(
            "events__lesson", "events__attempt__quiz", "attempts__quiz__lesson", "attempts__answers__question"
        )
        .first()
    )
    if enr is None:
        raise ApiError("Student not found.", 404)
    attempts = list(enr.attempts.all())
    finished = [a for a in attempts if a.finished_at and a.score is not None]
    problems = sorted(
        (ev for ev in enr.events.all() if ev.type == Event.PROBLEM),
        key=lambda ev: (ev.resolved_at is not None, -ev.created_at.timestamp()),
    )
    return {
        "id": enr.id,
        "course": {"id": enr.course_id, "title": enr.course.title},
        "student": {"name": enr.student.name, "email": enr.student.email},
        "joined_at": _dt(enr.joined_at),
        "last_activity_at": _dt(enr.last_activity_at),
        "avg_score_percent": round(100 * sum(a.score for a in finished) / len(finished)) if finished else None,
        "score_trend": [
            {"quiz": a.quiz.title, "score_percent": a.score_percent, "finished_at": _dt(a.finished_at)}
            for a in sorted(finished, key=lambda a: a.finished_at)
        ],
        "attempts": [_attempt_payload(a, with_expected=True) for a in attempts],
        "problems": [_problem_payload(ev) for ev in problems],
        "events": [_event_payload(ev) for ev in enr.events.all()],
    }


@api(methods=("PATCH",), teach=True)
def teach_problem(request, event_id: int):
    ev = (
        Event.objects.filter(pk=event_id, type=Event.PROBLEM, enrollment__course__in=_courses(request))
        .select_related("enrollment__student", "lesson", "attempt__quiz")
        .first()
    )
    if ev is None:
        raise ApiError("Problem not found.", 404)
    data = _body(request)
    fields = []
    if "resolved" in data:
        ev.resolved_at = timezone.now() if data["resolved"] else None
        fields.append("resolved_at")
    if "instructor_note" in data:
        ev.instructor_note = str(data["instructor_note"] or "").strip()[:2000]
        fields.append("instructor_note")
    if fields:
        ev.save(update_fields=fields)
    return _problem_payload(ev)


@api(teach=True)
def teach_review(request, course_id: int):
    course = _course(request, course_id)
    answers = (
        Answer.objects.filter(attempt__enrollment__course=course, status=Answer.NEEDS_REVIEW)
        .select_related("question", "attempt__quiz", "attempt__enrollment__student")
        .order_by("answered_at")
    )
    return {
        "answers": [
            {
                **_answer_payload(a),
                "expected": a.question.correct_answer,
                "accepted": a.question.accepted_answers_json,
                "quiz": a.attempt.quiz.title,
                "student": a.attempt.enrollment.student.name,
            }
            for a in answers
        ]
    }


@api(methods=("PATCH",), teach=True)
def teach_answer(request, answer_id: int):
    answer = (
        Answer.objects.filter(pk=answer_id, attempt__enrollment__course__in=_courses(request))
        .select_related("attempt__quiz")
        .first()
    )
    if answer is None:
        raise ApiError("Answer not found.", 404)
    status = _body(request).get("status")
    if status not in {Answer.CORRECT, Answer.INCORRECT, Answer.NEEDS_REVIEW}:
        raise ApiError("Invalid status.", errors={"status": ["Invalid."]})
    answer.status = status
    answer.save(update_fields=["status"])
    quizzes.recompute_score(answer.attempt)
    return {"ok": True, "score_percent": answer.attempt.score_percent}



def csrf_failure(request, reason=""):
    """CSRF errors as JSON for the API (the frontend shows the message); HTML elsewhere."""
    if request.path.startswith("/api/"):
        return JsonResponse(
            {"error": "Your session expired. Reload the page and try again.", "errors": {}}, status=403
        )
    from django.views.csrf import csrf_failure as default

    return default(request, reason=reason)
