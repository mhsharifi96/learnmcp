from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.db import connection, transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from learn.apps import ensure_instructors_group
from learn.forms import InstructorSignupForm, JoinCodeForm, JoinForm, RestoreForm
from learn.models import Course, Enrollment, Instructor, Student
from learn.services import ServiceError, enrollments, packs, tokens

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


# --------------------------------------------------------------------------- prompt results (no MCP)

PACK_TEXT = {
    "fa": {
        "dir": "rtl", "title": "نتیجه برای مدرس", "sent": "ارسال شد ✓ مدرس شما نتیجه را می‌بیند.",
        "already": "این نتیجه قبلاً ارسال شده بود.", "score": "نمره", "correct": "درست",
        "review": "سؤال‌های بی‌پاسخ یا غلط", "your": "پاسخ شما", "right": "پاسخ درست",
        "needs_review": "سؤال تشریحی؛ مدرس بررسی می‌کند", "copy": "این متن را در چت هوش مصنوعی پیست کنید تا اشتباه‌ها را توضیح دهد:",
        "paste_title": "ارسال نتیجه", "paste_lead": "متنی را که هوش مصنوعی ساخت (JSON) اینجا پیست کنید و ارسال کنید.",
        "send": "ارسال", "error": "خطا", "lesson_sent": "بازخورد درس ثبت شد", "close": "می‌توانید این صفحه را ببندید و به چت برگردید.",
    },
    "en": {
        "dir": "ltr", "title": "Result for your instructor", "sent": "Sent ✓ Your instructor can see the result.",
        "already": "This result was already sent.", "score": "Score", "correct": "correct",
        "review": "Questions to review", "your": "Your answer", "right": "Correct answer",
        "needs_review": "Free-text answer; your instructor will review it", "copy": "Paste this into your AI chat to go over your mistakes:",
        "paste_title": "Send a result", "paste_lead": "Paste the text your AI made (JSON) here and send it.",
        "send": "Send", "error": "Error", "lesson_sent": "Lesson feedback recorded", "close": "You can close this page and go back to the chat.",
    },
}


def _pack_lang(request, key: str) -> str:
    try:
        enrollment, _ = packs.read_key(key)
        return enrollment.student.lang
    except ServiceError:
        return "en" if request.headers.get("Accept-Language", "").startswith("en") else "fa"


@csrf_exempt
def pack_submit(request, key: str):
    """Receives the single result of a copy-paste prompt (HTML form POST, ?d= link, or pasted JSON)."""
    lang = _pack_lang(request, key)
    ctx = {"t": PACK_TEXT.get(lang, PACK_TEXT["fa"]), "key": key}
    form_fields = {k: v for k, v in request.POST.items() if k.startswith("a") and k[1:].isdigit()}
    raw = request.POST.get("d") or request.GET.get("d") or ""
    if request.method != "POST" and not raw:
        return render(request, "learn/pack.html", ctx)
    status = 200
    try:
        data = packs.parse_data(raw) if raw.strip() else {}
        data.update(form_fields)
        if not data:
            raise ServiceError("Nothing was sent.")
        origin = request.headers.get("Origin") or request.headers.get("Referer") or ""
        result = packs.submit(key, data, origin=origin)
        ctx.update(result=result, review=packs.review_text(result))
    except ServiceError as exc:
        ctx.update(error=str(exc), pasted=raw)
        status = 400
    if request.GET.get("format") == "json":
        resp = JsonResponse(ctx.get("result") or {"error": ctx.get("error")}, status=status)
        resp["Access-Control-Allow-Origin"] = "*"
        return resp
    return render(request, "learn/pack.html", ctx, status=status)
