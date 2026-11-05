from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.db import connection, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from learn.apps import ensure_instructors_group
from learn.forms import InstructorSignupForm, JoinCodeForm, JoinForm, RestoreForm
from learn.models import Course, Enrollment, Instructor, Student
from learn.services import ServiceError, enrollments, tokens

SESSION_ENROLLMENTS = "learnmcp_enrollments"
SESSION_STUDENT = "learnmcp_student_id"
SESSION_NEW_TOKENS = "learnmcp_new_tokens"


# --------------------------------------------------------------------------- helpers


def public_base_url(request) -> str:
    return settings.PUBLIC_BASE_URL or request.build_absolute_uri("/").rstrip("/")


def mcp_url(request, raw_token: str) -> str:
    return f"{public_base_url(request)}/s/{raw_token}/mcp"


def account_student(request) -> Student | None:
    """The student behind a logged-in student account (None for instructors / anonymous visitors)."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return None
    return getattr(user, "student", None)


def _session_enrollment_ids(request) -> list[int]:
    ids = list(request.session.get(SESSION_ENROLLMENTS, []))
    student = account_student(request)
    if student is not None:
        ids += [i for i in student.enrollments.values_list("id", flat=True) if i not in ids]
    return ids


def _remember_enrollment(request, enrollment: Enrollment) -> None:
    ids = _session_enrollment_ids(request)
    if enrollment.id not in ids:
        ids.append(enrollment.id)
    request.session[SESSION_ENROLLMENTS] = ids
    request.session[SESSION_STUDENT] = enrollment.student_id


def _stash_new_token(request, enrollment_id: int, raw: str) -> None:
    stash = dict(request.session.get(SESSION_NEW_TOKENS, {}))
    stash[str(enrollment_id)] = raw
    request.session[SESSION_NEW_TOKENS] = stash


def _pop_new_token(request, enrollment_id: int) -> str | None:
    stash = dict(request.session.get(SESSION_NEW_TOKENS, {}))
    raw = stash.pop(str(enrollment_id), None)
    request.session[SESSION_NEW_TOKENS] = stash
    return raw


def _my_enrollment(request, enrollment_id: int) -> Enrollment:
    if enrollment_id not in _session_enrollment_ids(request):
        raise Http404
    return get_object_or_404(Enrollment.objects.select_related("student", "course"), pk=enrollment_id)


# --------------------------------------------------------------------------- public


def home(request):
    return render(request, "learn/home.html")


def healthz(request):
    try:
        connection.ensure_connection()
    except Exception:
        return JsonResponse({"status": "error", "db": False}, status=503)
    return JsonResponse({"status": "ok", "db": True})


def signup(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect("admin:index")
    form = InstructorSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.is_staff = True
            user.save()
            user.groups.add(ensure_instructors_group())
            Instructor.objects.create(user=user, display_name=form.cleaned_data["display_name"])
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Welcome! Create your first class to get an invite link.")
        return redirect("admin:learn_course_add")
    return render(request, "learn/signup.html", {"form": form})


# --------------------------------------------------------------------------- students


def join_code(request):
    form = JoinCodeForm(request.GET or None)
    if request.GET and form.is_valid():
        if Course.objects.filter(join_code=form.cleaned_data["code"]).exists():
            return redirect("learn:join", code=form.cleaned_data["code"])
        form.add_error("code", "No class with this code. Check it with your instructor.")
    return render(request, "learn/join_code.html", {"form": form})


def join(request, code: str):
    course = get_object_or_404(Course.objects.select_related("instructor"), join_code=code.strip().upper())

    existing_student = None
    student_id = request.session.get(SESSION_STUDENT)
    if student_id:
        existing_student = Student.objects.filter(pk=student_id).first()
        if existing_student:
            already = Enrollment.objects.filter(student=existing_student, course=course).first()
            if already:
                messages.info(request, f"You have already joined {course.title}.")
                return redirect("learn:me")

    initial = {"name": existing_student.name, "email": existing_student.email} if existing_student else None
    form = JoinForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            enrollment, raw = enrollments.join(
                course,
                name=form.cleaned_data["name"],
                email=form.cleaned_data["email"],
                existing_student=existing_student,
            )
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect("learn:me")
        _remember_enrollment(request, enrollment)
        _stash_new_token(request, enrollment.id, raw)
        return redirect("learn:connect", enrollment_id=enrollment.id)

    return render(
        request,
        "learn/join.html",
        {"course": course, "form": form, "linked": existing_student is not None},
    )


def connect(request, enrollment_id: int):
    enrollment = _my_enrollment(request, enrollment_id)
    raw = _pop_new_token(request, enrollment.id)
    return render(
        request,
        "learn/connect.html",
        {
            "enrollment": enrollment,
            "mcp_url": mcp_url(request, raw) if raw else None,
            "other_classes": Enrollment.objects.filter(student=enrollment.student).exclude(pk=enrollment.pk).count(),
        },
    )


def my_data(request):
    ids = _session_enrollment_ids(request)
    qs = (
        Enrollment.objects.filter(pk__in=ids)
        .select_related("student", "course", "course__instructor")
        .prefetch_related("events__lesson", "attempts__quiz", "attempts__answers__question")
    )
    found = list(qs)
    # Drop ids that no longer exist (e.g. left on another device).
    request.session[SESSION_ENROLLMENTS] = [e.id for e in found]
    return render(request, "learn/me.html", {"enrollments": found})


def restore(request):
    form = RestoreForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        raw = tokens.extract_token_from_url(form.cleaned_data["url"])
        enrollment = tokens.resolve(raw) if raw else None
        if enrollment is None:
            form.add_error("url", "This URL is not valid or was regenerated.")
        else:
            for enr in Enrollment.objects.filter(student=enrollment.student):
                _remember_enrollment(request, enr)
            return redirect("learn:me")
    return render(request, "learn/restore.html", {"form": form})


@require_POST
def regenerate(request, enrollment_id: int):
    enrollment = _my_enrollment(request, enrollment_id)
    raw = tokens.assign_new_token(enrollment)
    _stash_new_token(request, enrollment.id, raw)
    messages.success(request, "Your old URL no longer works. Replace it in your AI connector settings.")
    return redirect(reverse("learn:connect", args=[enrollment.id]))


@require_POST
def leave(request, enrollment_id: int):
    enrollment = _my_enrollment(request, enrollment_id)
    title = enrollment.course.title
    enrollments.leave(enrollment)
    request.session[SESSION_ENROLLMENTS] = [i for i in _session_enrollment_ids(request) if i != enrollment_id]
    if not Student.objects.filter(pk=request.session.get(SESSION_STUDENT)).exists():
        request.session.pop(SESSION_STUDENT, None)
    messages.success(request, f"You left {title}. All data recorded for that class was deleted.")
    return redirect("learn:me")
