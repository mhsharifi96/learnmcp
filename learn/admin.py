"""Instructor panel built on Django admin.

Every ModelAdmin is scoped so an instructor only sees and edits their own classes
(PRD §10). Superusers (the platform operator) see everything.
"""

from django import forms
from django.contrib import admin, messages
from django.db import models
from django.db.models import Count
from django.http import Http404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

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
from learn.services import progress, quizzes


def instructor_for(request):
    return getattr(request.user, "instructor", None) if request.user.is_authenticated else None


class InstructorScopedMixin:
    """Filters querysets and FK choices to the current instructor.

    `course_path` is the ORM path from the model to its Course ("" for Course itself).
    """

    course_path = "course"

    def _course_filter(self, request) -> dict | None:
        if request.user.is_superuser:
            return None
        prefix = f"{self.course_path}__" if self.course_path else ""
        return {f"{prefix}instructor": instructor_for(request)}

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        flt = self._course_filter(request)
        if flt is None:
            return qs
        if instructor_for(request) is None:
            return qs.none()
        return qs.filter(**flt)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            inst = instructor_for(request)
            if db_field.related_model is Course:
                kwargs["queryset"] = Course.objects.filter(instructor=inst)
            elif db_field.related_model is Lesson:
                kwargs["queryset"] = Lesson.objects.filter(course__instructor=inst)
            elif db_field.related_model is Quiz:
                kwargs["queryset"] = Quiz.objects.filter(course__instructor=inst)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class ReadOnlyInline(admin.TabularInline):
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# --------------------------------------------------------------------------- course


class LessonInline(InstructorScopedMixin, admin.StackedInline):
    model = Lesson
    extra = 0
    fields = ("order", "title", "objectives", "content", "teaching_notes")
    show_change_link = True
    formfield_overrides = {models.TextField: {"widget": forms.Textarea(attrs={"rows": 4, "cols": 90})}}


class QuizInline(InstructorScopedMixin, admin.TabularInline):
    model = Quiz
    extra = 0
    fields = ("title", "lesson", "question_count")
    readonly_fields = ("question_count",)
    show_change_link = True

    @admin.display(description="Questions")
    def question_count(self, obj):
        return obj.questions.count() if obj.pk else "—"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        # Only lessons of the class being edited.
        if db_field.name == "lesson" and request.resolver_match and request.resolver_match.kwargs.get("object_id"):
            field.queryset = field.queryset.filter(course_id=request.resolver_match.kwargs["object_id"])
        return field


@admin.register(Course)
class CourseAdmin(InstructorScopedMixin, admin.ModelAdmin):
    course_path = ""
    list_display = ("title", "join_code", "student_count", "lesson_count", "dashboard_link", "created_at")
    search_fields = ("title",)
    readonly_fields = ("join_code", "invite_link", "dashboard_link")
    inlines = [LessonInline, QuizInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _students=Count("enrollments", distinct=True), _lessons=Count("lessons", distinct=True)
        )

    def get_fields(self, request, obj=None):
        fields = ["title", "description"]
        if request.user.is_superuser:
            fields.insert(0, "instructor")
        if obj:
            fields += ["join_code", "invite_link", "dashboard_link"]
        return fields

    def save_model(self, request, obj, form, change):
        # Instructors always own the classes they create; superusers pick the instructor.
        if not request.user.is_superuser:
            inst = instructor_for(request)
            if inst is None:
                inst, _ = Instructor.objects.get_or_create(
                    user=request.user, defaults={"display_name": request.user.get_username()}
                )
            obj.instructor = inst
        super().save_model(request, obj, form, change)

    @admin.display(description="Students", ordering="_students")
    def student_count(self, obj):
        return getattr(obj, "_students", obj.enrollments.count())

    @admin.display(description="Lessons", ordering="_lessons")
    def lesson_count(self, obj):
        return getattr(obj, "_lessons", obj.lessons.count())

    @admin.display(description="Invite link")
    def invite_link(self, obj):
        if not obj.pk:
            return "—"
        join_path = reverse("learn:join", args=[obj.join_code])
        return format_html(
            '<span class="learnmcp-invite" data-path="{}">'
            '<input type="text" readonly size="50" value="{}" class="vTextField">'
            ' <button type="button" class="button learnmcp-copy">Copy</button></span>'
            '<p class="help">Share this link (or the code {}) with your students.</p>',
            join_path,
            join_path,
            obj.join_code,
        )

    @admin.display(description="Dashboard")
    def dashboard_link(self, obj):
        if not obj.pk:
            return "—"
        return format_html('<a class="button" href="{}">Open dashboard</a>', reverse("admin:learn_course_dashboard", args=[obj.pk]))

    class Media:
        js = ("learn/admin.js",)

    def get_urls(self):
        custom = [
            path(
                "<path:object_id>/dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="learn_course_dashboard",
            )
        ]
        return custom + super().get_urls()

    def dashboard_view(self, request, object_id):
        course = self.get_queryset(request).filter(pk=object_id).first()
        if course is None or not self.has_view_permission(request, course):
            raise Http404
        data = progress.course_dashboard(course)
        calls = ToolCall.objects.filter(enrollment__course=course)
        total_calls = calls.count()
        ok_calls = calls.filter(ok=True).count()
        context = {
            **self.admin_site.each_context(request),
            "title": f"Dashboard — {course.title}",
            "course": course,
            "opts": self.model._meta,
            "tool_calls_total": total_calls,
            "tool_calls_ok_percent": round(100 * ok_calls / total_calls) if total_calls else None,
            **data,
        }
        return TemplateResponse(request, "admin/learn/course/dashboard.html", context)


# --------------------------------------------------------------------------- lessons, quizzes


@admin.register(Lesson)
class LessonAdmin(InstructorScopedMixin, admin.ModelAdmin):
    list_display = ("title", "course", "order")
    list_filter = (("course", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("title", "content")
    ordering = ("course", "order")


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = "__all__"
        widgets = {
            "prompt": forms.Textarea(attrs={"rows": 2, "cols": 40}),
            "options_json": forms.Textarea(attrs={"rows": 2, "cols": 30}),
            "accepted_answers_json": forms.Textarea(attrs={"rows": 2, "cols": 24}),
            "explanation": forms.Textarea(attrs={"rows": 2, "cols": 30}),
            "correct_answer": forms.TextInput(attrs={"size": 14}),
            "concept": forms.TextInput(attrs={"size": 14}),
            "order": forms.NumberInput(attrs={"style": "width:4em"}),
        }


class QuestionInline(admin.TabularInline):
    model = Question
    form = QuestionForm
    extra = 1
    fields = (
        "order",
        "type",
        "prompt",
        "options_json",
        "correct_answer",
        "accepted_answers_json",
        "explanation",
        "concept",
    )


@admin.register(Quiz)
class QuizAdmin(InstructorScopedMixin, admin.ModelAdmin):
    list_display = ("title", "course", "lesson", "question_count")
    list_filter = (("course", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("title",)
    inlines = [QuestionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_questions=Count("questions"))

    @admin.display(description="Questions", ordering="_questions")
    def question_count(self, obj):
        return obj._questions


@admin.register(Question)
class QuestionAdmin(InstructorScopedMixin, admin.ModelAdmin):
    course_path = "quiz__course"
    form = QuestionForm
    list_display = ("prompt_short", "quiz", "type", "concept", "order")
    list_filter = ("type", ("quiz", admin.RelatedOnlyFieldListFilter))
    search_fields = ("prompt", "concept")

    def has_module_permission(self, request):
        return request.user.is_superuser  # instructors edit questions inside the quiz page

    @admin.display(description="Question")
    def prompt_short(self, obj):
        return obj.prompt[:80]


# --------------------------------------------------------------------------- student activity (read-only)


class EventInline(ReadOnlyInline):
    model = Event
    fields = ("created_at", "type", "lesson", "concept", "note", "client")
    readonly_fields = fields
    show_change_link = False
    ordering = ("-created_at",)


class AttemptInline(ReadOnlyInline):
    model = QuizAttempt
    fields = ("quiz", "started_at", "finished_at", "score_display")
    readonly_fields = fields

    @admin.display(description="Score")
    def score_display(self, obj):
        return "—" if obj.score is None else f"{obj.score_percent}%"


@admin.register(Enrollment)
class EnrollmentAdmin(InstructorScopedMixin, admin.ModelAdmin):
    list_display = ("student_name", "student_email", "course", "joined_at", "last_activity_at")
    list_filter = (("course", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("student__name", "student__email")
    fields = ("student", "course", "consent_at", "joined_at", "last_activity_at", "token_hint", "token_rotated_at")
    readonly_fields = fields
    inlines = [AttemptInline, EventInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Student", ordering="student__name")
    def student_name(self, obj):
        return obj.student.name

    @admin.display(description="Email", ordering="student__email")
    def student_email(self, obj):
        return obj.student.email


class AnswerInline(ReadOnlyInline):
    model = Answer
    fields = ("question", "raw_answer", "status", "answered_at")
    readonly_fields = fields


@admin.register(QuizAttempt)
class QuizAttemptAdmin(InstructorScopedMixin, admin.ModelAdmin):
    course_path = "enrollment__course"
    list_display = ("quiz", "student", "started_at", "finished_at", "score_display")
    list_filter = (("quiz", admin.RelatedOnlyFieldListFilter),)
    search_fields = ("enrollment__student__name",)
    fields = ("enrollment", "quiz", "started_at", "finished_at", "score")
    readonly_fields = fields
    inlines = [AnswerInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Student", ordering="enrollment__student__name")
    def student(self, obj):
        return obj.enrollment.student.name

    @admin.display(description="Score", ordering="score")
    def score_display(self, obj):
        return "—" if obj.score is None else f"{obj.score_percent}%"


@admin.register(Answer)
class AnswerAdmin(InstructorScopedMixin, admin.ModelAdmin):
    """Instructors review short answers that need a human decision."""

    course_path = "attempt__enrollment__course"
    list_display = ("student", "question", "raw_answer", "status", "answered_at")
    list_filter = ("status", ("attempt__quiz", admin.RelatedOnlyFieldListFilter))
    search_fields = ("raw_answer", "attempt__enrollment__student__name")
    fields = ("student", "question", "expected", "raw_answer", "status", "answered_at")
    readonly_fields = ("student", "question", "expected", "raw_answer", "answered_at")
    actions = ["mark_correct", "mark_incorrect"]

    def has_add_permission(self, request):
        return False

    @admin.display(description="Student", ordering="attempt__enrollment__student__name")
    def student(self, obj):
        return obj.attempt.enrollment.student.name

    @admin.display(description="Expected answer")
    def expected(self, obj):
        accepted = ", ".join(obj.question.accepted_answers_json or [])
        return f"{obj.question.correct_answer}" + (f" (also: {accepted})" if accepted else "")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        quizzes.recompute_score(obj.attempt)

    def _set_status(self, request, queryset, status):
        attempts = set()
        for answer in queryset.select_related("attempt"):
            answer.status = status
            answer.save(update_fields=["status"])
            attempts.add(answer.attempt)
        for attempt in attempts:
            quizzes.recompute_score(attempt)
        self.message_user(request, f"{queryset.count()} answer(s) updated; scores recalculated.", messages.SUCCESS)

    @admin.action(description="Mark selected answers as correct", permissions=["change"])
    def mark_correct(self, request, queryset):
        self._set_status(request, queryset, Answer.CORRECT)

    @admin.action(description="Mark selected answers as incorrect", permissions=["change"])
    def mark_incorrect(self, request, queryset):
        self._set_status(request, queryset, Answer.INCORRECT)


@admin.register(Event)
class EventAdmin(InstructorScopedMixin, admin.ModelAdmin):
    course_path = "enrollment__course"
    list_display = ("created_at", "type", "student", "lesson", "concept", "client")
    list_filter = ("type", ("enrollment__course", admin.RelatedOnlyFieldListFilter))
    search_fields = ("concept", "note", "enrollment__student__name")
    readonly_fields = ("enrollment", "type", "lesson", "concept", "note", "client", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Student", ordering="enrollment__student__name")
    def student(self, obj):
        return obj.enrollment.student.name


# --------------------------------------------------------------------------- operator-only


class OperatorOnlyAdmin(admin.ModelAdmin):
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Instructor)
class InstructorAdmin(OperatorOnlyAdmin):
    list_display = ("display_name", "user", "created_at")
    search_fields = ("display_name", "user__username", "user__email")


@admin.register(Student)
class StudentAdmin(OperatorOnlyAdmin):
    list_display = ("name", "email", "created_at")
    search_fields = ("name", "email")


@admin.register(ToolCall)
class ToolCallAdmin(OperatorOnlyAdmin):
    list_display = ("created_at", "tool", "client", "ok", "error", "duration_ms", "enrollment")
    list_filter = ("tool", "client", "ok")
    readonly_fields = [f.name for f in ToolCall._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
