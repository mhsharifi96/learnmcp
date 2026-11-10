"""JSON API for the Next.js frontend (same origin, Django session + CSRF cookie).

Student endpoints reuse the anonymous-session model of the server-rendered pages: the
browser session remembers which enrollments belong to this visitor.

Instructor endpoints (/api/teach/...) require a logged-in staff user and are scoped to the
instructor's own classes (superusers see everything), mirroring the admin scoping.
"""

import json
import time
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from learn import views as pages
from learn.apps import ensure_instructors_group
from learn.forms import InstructorSignupForm
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
from learn.services import ServiceError, accounts, authoring, covers, courses, enrollments, grading, history, packs, progress, quizzes, tokens


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


def _student_payload(student: Student | None) -> dict | None:
    if student is None:
        return None
    return {
        "name": student.name,
        "email": student.email,
        "email_verified": student.email_verified,
        "email_reminders": student.email_reminders,
        "lang": student.lang,
    }


@api()
def whoami(request):
    return {"user": _user_payload(request.user), "student": _student_payload(pages.account_student(request))}


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


# =========================================================================== student accounts

SESSION_VERIFY_SENT = "learnmcp_verify_sent_at"
RESEND_COOLDOWN_SECONDS = 60


def _send_verification(request, student: Student) -> bool:
    request.session[SESSION_VERIFY_SENT] = time.time()
    return accounts.send_verification(student, pages.public_base_url(request))


def _login_student(request, student: Student) -> None:
    login(request, student.user, backend="django.contrib.auth.backends.ModelBackend")
    # Keep this browser linked to the student's classes (MCP setup pages, /me).
    request.session[pages.SESSION_STUDENT] = student.id
    request.session[pages.SESSION_ENROLLMENTS] = list(student.enrollments.values_list("id", flat=True))


def _account(request) -> Student:
    student = pages.account_student(request)
    if student is None:
        raise ApiError("Please log in with your student account.", 401)
    return student


@api(methods=("POST",))
def student_signup(request):
    data = _body(request)
    name = str(data.get("name", "")).strip()
    email = accounts.normalize_email(str(data.get("email", "")))
    p1, p2 = str(data.get("password1", "")), str(data.get("password2", ""))
    errors: dict[str, list[str]] = {}
    if not name:
        errors["name"] = ["Enter your name."]
    elif len(name) > 120:
        errors["name"] = ["Use at most 120 characters."]
    try:
        validate_email(email)
    except ValidationError:
        errors["email"] = ["Enter a valid email address."]
    else:
        if accounts.email_taken(email):
            errors["email"] = ["An account with this email already exists. Log in instead."]
    if p1 != p2:
        errors["password2"] = ["The two passwords don't match."]
    else:
        try:
            validate_password(p1)
        except ValidationError as exc:
            errors["password1"] = list(exc.messages)
    if errors:
        raise ApiError("Please fix the highlighted fields.", errors=errors)

    claim = None
    sid = request.session.get(pages.SESSION_STUDENT)
    if sid:
        claim = Student.objects.filter(pk=sid, user__isnull=True).first()
    student = accounts.create_student_account(
        name=name, email=email, password=p1, lang=str(data.get("lang", "fa")), claim=claim
    )
    _login_student(request, student)
    sent = _send_verification(request, student)
    return {"student": _student_payload(student), "email_sent": sent}


@api(methods=("POST",))
def student_login(request):
    data = _body(request)
    email = accounts.normalize_email(str(data.get("email", "")))
    user = authenticate(request, username=email, password=str(data.get("password", "")))
    student = getattr(user, "student", None) if user else None
    if student is None:
        raise ApiError("Wrong email or password.", 400)
    _login_student(request, student)
    return {"student": _student_payload(student)}


@api(methods=("POST",))
def verify_email(request):
    student = accounts.verify(str(_body(request).get("token", "")))
    return {"ok": True, "student": _student_payload(student)}


@api(methods=("POST",))
def resend_verification(request):
    student = _account(request)
    if student.email_verified:
        return {"ok": True, "already_verified": True}
    last = request.session.get(SESSION_VERIFY_SENT) or 0
    wait = int(RESEND_COOLDOWN_SECONDS - (time.time() - last))
    if wait > 0:
        raise ApiError(f"Please wait {wait} seconds before sending another email.", 429)
    if not _send_verification(request, student):
        raise ApiError("We couldn't send the email right now. Try again later.", 503)
    return {"ok": True}


@api(methods=("PATCH",))
def my_settings(request):
    student = _account(request)
    data = _body(request)
    fields = []
    if "email_reminders" in data:
        student.email_reminders = bool(data["email_reminders"])
        fields.append("email_reminders")
    if "name" in data:
        name = str(data["name"] or "").strip()
        if not name or len(name) > 120:
            raise ApiError("Please fix the highlighted fields.", errors={"name": ["Enter your name."]})
        student.name = name
        fields.append("name")
    if data.get("lang") in ("fa", "en"):
        student.lang = data["lang"]
        fields.append("lang")
    if fields:
        student.save(update_fields=fields)
    return {"student": _student_payload(student)}


# =========================================================================== students


@api()
def catalog(request):
    """Public list of classes (instructors can hide theirs). Join codes are only for classes that are listed."""
    student = pages.account_student(request)
    joined = set(Enrollment.objects.filter(student=student).values_list("course_id", flat=True)) if student else set()
    qs = (
        Course.objects.filter(listed=True)
        .defer("image_data")
        .select_related("instructor")
        .annotate(
            _students=Count("enrollments", distinct=True),
            _lessons=Count("lessons", filter=Q(lessons__draft=False), distinct=True),
        )
        .order_by("-created_at", "-id")
    )
    return {
        "classes": [
            {
                "id": c.id,
                "code": c.join_code,
                "title": c.title,
                "description": c.description,
                "category": c.category,
                "instructor": c.instructor.display_name,
                "instructor_id": c.instructor_id,
                "lessons": c._lessons,
                "students": c._students,
                "joined": c.id in joined,
                "updated": _dt(max(filter(None, [c.created_at, c.image_updated_at]))),
                **covers.payload(c),
            }
            for c in qs
        ]
    }


@api()
def class_info(request, code: str):
    course = (
        Course.objects.defer("image_data").select_related("instructor").filter(join_code=code.strip().upper()).first()
    )
    if course is None:
        raise ApiError("No class with this code. Check it with your instructor.", 404)
    student = pages.account_student(request)
    mine = Enrollment.objects.filter(student=student, course=course).first() if student else None
    already = mine is not None
    # Lesson titles (public, for listed classes only) so the join page shows what the class covers.
    # Draft lessons stay hidden.
    titles = course.lessons.published().order_by("order", "id").values_list("title", flat=True)
    lessons = (
        [{"order": n, "title": title} for n, title in enumerate(titles, start=1)]
        if course.listed
        else []
    )
    return {
        "code": course.join_code,
        "title": course.title,
        "description": course.description,
        "instructor": course.instructor.display_name,
        "listed": course.listed,
        "lessons": lessons,
        "linked": student is not None,
        "already_joined": already,
        "pending": bool(mine and not mine.approved),
        "requires_approval": course.requires_approval,
        "quizzes": course.quizzes.published().count() if course.listed else 0,
        "student": _student_payload(student),
        **covers.payload(course),
    }


def class_image(request, code: str):
    """The uploaded cover photo of a class. Cached for a long time: the URL changes on every upload."""
    course = Course.objects.filter(join_code=code.strip().upper()).only("image_data", "image_type").first()
    if course is None or not course.image_data:
        return HttpResponse(status=404)
    resp = HttpResponse(bytes(course.image_data), content_type=course.image_type or "image/jpeg")
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    resp["X-Content-Type-Options"] = "nosniff"
    return resp


@api(methods=("POST",))
def join_class(request, code: str):
    course = Course.objects.filter(join_code=code.strip().upper()).first()
    if course is None:
        raise ApiError("No class with this code.", 404)
    student = _account(request)
    if not student.email_verified:
        raise ApiError("Confirm your email first. We sent you a link.", 403)
    if not _body(request).get("consent"):
        raise ApiError(
            "Please fix the highlighted fields.", errors={"consent": ["Please agree before joining."]}
        )
    enrollment, raw = enrollments.join(course, name=student.name, email=student.email, existing_student=student)
    pages._remember_enrollment(request, enrollment)
    pages._stash_new_token(request, enrollment.id, raw)
    return {"enrollment_id": enrollment.id, "pending": not enrollment.approved}


def _pending_error() -> ApiError:
    return ApiError("Your registration is waiting for approval by the site admin.", 403)


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
    if not enr.approved:
        # Keep the personal link hidden until approval; it is made fresh once the admin approves.
        return {"enrollment_id": enr.id, "course": enr.course.title, "pending": True, "mcp_url": None,
                "token_hint": "", "other_classes": 0}
    raw = pages._pop_new_token(request, enr.id)
    return {
        "enrollment_id": enr.id,
        "pending": False,
        "course": enr.course.title,
        "mcp_url": pages.mcp_url(request, raw) if raw else None,
        "token_hint": enr.token_hint,
        "other_classes": Enrollment.objects.filter(student=enr.student).exclude(pk=enr.pk).count(),
    }


@api(methods=("POST",))
def regenerate(request, enrollment_id: int):
    enr = _my_enrollment(request, enrollment_id)
    if not enr.approved:
        raise _pending_error()
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


@api()
def study(request, enrollment_id: int):
    """Lessons and quizzes of one class, for the copy-a-prompt page (AI apps without MCP)."""
    enr = _my_enrollment(request, enrollment_id)
    if not enr.approved:
        raise _pending_error()
    data = courses.list_courses(enr)
    course = next((c for c in data["courses"] if c["course_id"] == enr.course_id), None)
    # What already reached the instructor, per lesson and quiz (newest first).
    sent_lessons: dict[int, dict] = {}
    for ev in enr.events.filter(type=Event.LESSON_FEEDBACK, lesson__isnull=False).order_by("-created_at"):
        if ev.lesson_id not in sent_lessons:
            fb = history.feedback_fields(ev)
            sent_lessons[ev.lesson_id] = {"at": _dt(ev.created_at), "understood": fb["understood"]}
    sent_quizzes: dict[int, dict] = {}
    for a in enr.attempts.filter(finished_at__isnull=False).order_by("-finished_at"):
        if a.quiz_id not in sent_quizzes:
            sent_quizzes[a.quiz_id] = {"at": _dt(a.finished_at), "score_percent": a.score_percent}
    if course:
        for lesson in course["lessons"]:
            lesson["sent"] = sent_lessons.get(lesson["lesson_id"])
            for q in lesson["quizzes"]:
                q["last"] = sent_quizzes.get(q["quiz_id"])
        for q in course["class_quizzes"]:
            q["last"] = sent_quizzes.get(q["quiz_id"])
    return {"enrollment_id": enr.id, "course": course}


@api(methods=("POST",))
def study_prompt(request, enrollment_id: int):
    enr = _my_enrollment(request, enrollment_id)
    if not enr.approved:
        raise _pending_error()
    data = _body(request)
    base = pages.public_base_url(request)
    if data.get("lesson_id"):
        text = packs.lesson_prompt(enr, int(data["lesson_id"]), base)
    elif data.get("quiz_id"):
        text = packs.quiz_prompt(enr, int(data["quiz_id"]), base)
    else:
        raise ApiError("Pick a lesson or a quiz.")
    return {"prompt": text}


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
        "student": _student_payload(pages.account_student(request)),
        "enrollments": [
            {
                "id": e.id,
                "course": e.course.title,
                "course_code": e.course.join_code,
                "instructor": e.course.instructor.display_name,
                "student": {"name": e.student.name, "email": e.student.email},
                "joined_at": _dt(e.joined_at),
                "approved": e.approved,
                "consent_at": _dt(e.consent_at),
                "token_hint": e.token_hint,
                "attempts": [_attempt_payload(a) for a in e.attempts.all()],
                "events": [_event_payload(ev) for ev in e.events.all()],
                "progress": history.progress(e),
                "timeline": history.timeline(e),
            }
            for e in found
        ]
    }


@api(methods=("POST",))
def restore(request):
    raw = tokens.extract_token_from_url(str(_body(request).get("url", "")))
    enr = tokens.resolve(raw) if raw else None
    me = pages.account_student(request)
    if enr is not None and me is not None and enr.student_id != me.id:
        raise ApiError("This link belongs to another student.", errors={"url": ["Not yours."]})
    if enr is None:
        raise ApiError("This URL is not valid or was regenerated.", errors={"url": ["Not valid."]})
    for e in Enrollment.objects.filter(student=enr.student):
        pages._remember_enrollment(request, e)
    return {"ok": True}


# =========================================================================== instructors


def _instructor(request) -> Instructor | None:
    return getattr(request.user, "instructor", None)


def _courses(request):
    qs = Course.objects.defer("image_data").select_related("instructor")
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
        "kind": lesson.kind,
        "brief": lesson.brief,
        "objectives": lesson.objectives,
        "content": lesson.content,
        "teaching_notes": lesson.teaching_notes,
        "draft": lesson.draft,
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
        "draft": quiz.draft,
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
        "reminder_after_days": course.reminder_after_days,
        "listed": course.listed,
        "created_at": _dt(course.created_at),
        **covers.payload(course),
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
        data = _body(request)
        if "reminder_after_days" in data:
            try:
                days = int(data["reminder_after_days"] or 0)
            except (TypeError, ValueError):
                days = -1
            if not 0 <= days <= 365:
                raise ApiError(
                    "Please fix the highlighted fields.",
                    errors={"reminder_after_days": ["Choose 0 (off) to 365 days."]},
                )
            data["reminder_after_days"] = days
        _apply(course, data, ("title", "description", "reminder_after_days", "listed"))
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


LESSON_FIELDS = ("order", "title", "kind", "brief", "objectives", "content", "teaching_notes", "draft")


@api(methods=("POST",), teach=True)
def teach_lessons(request, course_id: int):
    course = _course(request, course_id)
    data = _body(request)
    data.setdefault("order", (course.lessons.order_by("-order").values_list("order", flat=True).first() or 0) + 1)
    lesson = _apply(Lesson(course=course), data, LESSON_FIELDS)
    return JsonResponse(_lesson_payload(lesson), status=201)


@api(methods=("PATCH", "DELETE"), teach=True)
def teach_lesson(request, lesson_id: int):
    lesson = _lesson(request, lesson_id)
    if request.method == "DELETE":
        lesson.delete()
        return {"ok": True}
    return _lesson_payload(
        _apply(lesson, _body(request), LESSON_FIELDS)
    )


QUIZ_FIELDS = ("title", "mode", "prompt", "ai_question_count", "draft")


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


@api(methods=("POST", "DELETE"), teach=True)
def teach_course_image(request, course_id: int):
    """Upload (multipart field "image") or remove the class cover photo."""
    course = _course(request, course_id)
    if request.method == "DELETE":
        covers.clear_image(course)
    else:
        upload = request.FILES.get("image")
        if upload is None:
            raise ApiError("Choose an image file.")
        if upload.size > covers.MAX_BYTES:
            raise ApiError("The image is too large. Use a JPG, PNG or WebP under 3 MB.")
        covers.set_image(course, upload.read())
    return covers.payload(course)


@api(methods=("POST",), teach=True)
def teach_ai_prompt(request, course_id: int):
    """Turn the instructor's goal into a prompt for their own AI."""
    course = _course(request, course_id)
    data = _body(request)
    return {"prompt": authoring.build_prompt(course, str(data.get("goal") or ""), str(data.get("target") or ""))}


@api(methods=("POST",), teach=True)
def teach_import(request, course_id: int):
    """Create lessons and quizzes from the JSON the instructor's AI made. Everything starts as a draft."""
    course = _course(request, course_id)
    return authoring.import_json(course, str(_body(request).get("json") or ""))


@api(methods=("POST",), teach=True)
def teach_publish(request, course_id: int):
    """Publish every draft lesson and quiz of the class."""
    return authoring.publish_all(_course(request, course_id))


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
