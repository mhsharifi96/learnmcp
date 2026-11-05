import secrets
import string

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

JOIN_CODE_ALPHABET = string.ascii_uppercase + string.digits
# Avoid characters that are easy to confuse when read aloud or typed.
JOIN_CODE_ALPHABET = "".join(c for c in JOIN_CODE_ALPHABET if c not in "O0I1L")


def generate_join_code(length: int = 8) -> str:
    return "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(length))


class Instructor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="instructor")
    display_name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name


class Course(models.Model):
    instructor = models.ForeignKey(Instructor, on_delete=models.CASCADE, related_name="courses")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    join_code = models.CharField(max_length=16, unique=True, editable=False)
    reminder_after_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Email a student after this many days without studying (0 = off). Repeats every N days.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "class"
        verbose_name_plural = "classes"

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.join_code:
            code = generate_join_code()
            while Course.objects.filter(join_code=code).exists():
                code = generate_join_code()
            self.join_code = code
        super().save(*args, **kwargs)


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    order = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=200)
    objectives = models.TextField(blank=True, help_text="One objective per line.")
    brief = models.TextField(
        "lesson prompt",
        blank=True,
        help_text=(
            "A short prompt describing the lesson (topic, level, focus). If the lesson text below is empty, "
            "the student's AI builds the full lesson plan from this prompt."
        ),
    )
    content = models.TextField(
        "lesson text",
        blank=True,
        help_text="Optional. Write the full lesson yourself, or leave empty to let the AI build it from the prompt.",
    )
    teaching_notes = models.TextField(
        blank=True,
        help_text="Instructions for the AI tutor (tone, examples to use, common mistakes to watch for).",
    )

    class Meta:
        ordering = ["course", "order", "id"]

    def __str__(self):
        return f"{self.order}. {self.title}"

    @property
    def objectives_list(self) -> list[str]:
        return [line.strip("-• ").strip() for line in self.objectives.splitlines() if line.strip()]


    def clean(self):
        if not self.brief.strip() and not self.content.strip():
            raise ValidationError({"brief": "Write a lesson prompt or the full lesson text."})


class Quiz(models.Model):
    MANUAL = "manual"
    AI = "ai"
    MODE_CHOICES = [
        (MANUAL, "I write the questions (graded by the server)"),
        (AI, "The AI writes the questions from my prompt"),
    ]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="quizzes")
    lesson = models.ForeignKey(
        Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="quizzes"
    )
    title = models.CharField(max_length=200)
    mode = models.CharField(max_length=10, choices=MODE_CHOICES, default=MANUAL)
    prompt = models.TextField(
        blank=True,
        help_text=(
            "AI mode only. Describe the quiz you want, e.g. \"8 questions on the past simple, mix multiple choice "
            "and fill-in-the-gap, A2 level, focus on irregular verbs\"."
        ),
    )
    ai_question_count = models.PositiveSmallIntegerField(
        "number of questions", default=5, help_text="AI mode only. How many questions the AI asks."
    )

    class Meta:
        ordering = ["course", "lesson__order", "id"]
        verbose_name_plural = "quizzes"

    def __str__(self):
        return self.title

    @property
    def is_ai(self) -> bool:
        return self.mode == self.AI

    def manual_questions(self):
        return self.questions.filter(attempt__isnull=True)

    def clean(self):
        errors = {}
        if self.lesson_id and self.course_id and self.lesson.course_id != self.course_id:
            errors["lesson"] = "The lesson must belong to the same class."
        if self.mode == self.AI:
            if not self.prompt.strip():
                errors["prompt"] = "Write a prompt for the AI to build the quiz from."
            if not 1 <= (self.ai_question_count or 0) <= 50:
                errors["ai_question_count"] = "Choose between 1 and 50 questions."
        if errors:
            raise ValidationError(errors)


class Question(models.Model):
    MCQ = "mcq"
    SHORT = "short"
    TYPE_CHOICES = [(MCQ, "Multiple choice"), (SHORT, "Short answer")]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="questions")
    attempt = models.ForeignKey(
        "QuizAttempt",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="generated_questions",
        help_text="Set for questions the student's AI generated during this attempt (AI-mode quizzes).",
    )
    order = models.PositiveIntegerField(default=1)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=MCQ)
    prompt = models.TextField()
    options_json = models.JSONField(
        default=list, blank=True, help_text='Multiple choice only. A JSON list, e.g. ["Paris", "Rome", "Madrid"].'
    )
    correct_answer = models.CharField(
        max_length=500,
        help_text="Multiple choice: the option letter (A, B, …) or the exact option text. Short answer: the model answer.",
    )
    accepted_answers_json = models.JSONField(
        default=list, blank=True, help_text='Short answer: other accepted answers, e.g. ["H2O", "water"].'
    )
    explanation = models.TextField(blank=True, help_text="Shown to the student after they answer.")
    concept = models.CharField(max_length=120, blank=True, help_text="The concept this question tests.")

    class Meta:
        ordering = ["quiz", "order", "id"]

    def __str__(self):
        return f"Q{self.order}: {self.prompt[:60]}"

    def clean(self):
        errors = {}
        if not isinstance(self.options_json, list) or not all(isinstance(o, str) for o in self.options_json):
            errors["options_json"] = "Options must be a JSON list of strings."
        if not isinstance(self.accepted_answers_json, list) or not all(
            isinstance(o, str) for o in self.accepted_answers_json
        ):
            errors["accepted_answers_json"] = "Accepted answers must be a JSON list of strings."
        if self.type == self.MCQ and not errors.get("options_json"):
            if len(self.options_json) < 2:
                errors["options_json"] = "A multiple choice question needs at least two options."
            else:
                from learn.services.grading import resolve_mcq_correct_index

                if resolve_mcq_correct_index(self) is None:
                    errors["correct_answer"] = "Must be an option letter (A, B, …) or match one option's text."
        if errors:
            raise ValidationError(errors)


class Student(models.Model):
    LANG_CHOICES = [("fa", "فارسی"), ("en", "English")]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="student",
        help_text="Student account (email + password). Empty for students who joined before accounts existed.",
    )
    name = models.CharField(max_length=120)
    email = models.EmailField()
    email_verified_at = models.DateTimeField(null=True, blank=True)
    lang = models.CharField(max_length=5, choices=LANG_CHOICES, default="fa", help_text="Language of emails.")
    email_reminders = models.BooleanField(
        default=True, help_text="Receive inactivity reminder emails from instructors."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    def __str__(self):
        return f"{self.name} <{self.email}>"


class Enrollment(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    token_hash = models.CharField(max_length=64, unique=True, editable=False)
    token_hint = models.CharField(max_length=8, blank=True, editable=False, help_text="Last characters of the token.")
    consent_at = models.DateTimeField()
    joined_at = models.DateTimeField(auto_now_add=True)
    token_rotated_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    last_reminder_at = models.DateTimeField(null=True, blank=True, help_text="Last inactivity reminder email.")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["student", "course"], name="unique_student_course")]
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.student.name} in {self.course.title}"

    def touch(self):
        now = timezone.now()
        Enrollment.objects.filter(pk=self.pk).update(last_activity_at=now)
        self.last_activity_at = now


class QuizAttempt(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attempts")
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True, help_text="Share of questions answered correctly (0–1).")
    summary = models.TextField(
        blank=True, help_text="Short report from the student's AI: what happened and where the student went wrong."
    )
    weak_concepts_json = models.JSONField(default=list, blank=True, help_text="Concepts the student should review.")

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.quiz} — {self.enrollment.student.name}"

    @property
    def score_percent(self):
        return None if self.score is None else round(self.score * 100)


class Answer(models.Model):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    NEEDS_REVIEW = "needs_review"
    STATUS_CHOICES = [(CORRECT, "Correct"), (INCORRECT, "Incorrect"), (NEEDS_REVIEW, "Needs review")]

    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    raw_answer = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["attempt", "question"], name="unique_attempt_question")]
        ordering = ["answered_at"]

    def __str__(self):
        return f"{self.question} → {self.raw_answer[:40]}"

    @property
    def is_correct(self) -> bool | None:
        if self.status == self.NEEDS_REVIEW:
            return None
        return self.status == self.CORRECT


class Event(models.Model):
    LESSON_STARTED = "lesson_started"
    LESSON_FEEDBACK = "lesson_feedback"
    PROBLEM = "problem"
    PROGRESS_VIEWED = "progress_viewed"
    QUIZ_STARTED = "quiz_started"
    QUIZ_FINISHED = "quiz_finished"
    TYPE_CHOICES = [
        (LESSON_STARTED, "Lesson started"),
        (LESSON_FEEDBACK, "Lesson feedback"),
        (PROBLEM, "Problem reported"),
        (PROGRESS_VIEWED, "Progress viewed"),
        (QUIZ_STARTED, "Quiz started"),
        (QUIZ_FINISHED, "Quiz finished"),
    ]

    # Problem categories (type == PROBLEM).
    CAT_CONCEPT = "concept"
    CAT_REPEATED = "repeated_mistake"
    CAT_QUIZ = "quiz_mistakes"
    CAT_PREREQUISITE = "prerequisite"
    CAT_ENGAGEMENT = "engagement"
    CAT_TECHNICAL = "technical"
    CAT_OTHER = "other"
    CATEGORY_CHOICES = [
        (CAT_CONCEPT, "Doesn't understand a concept"),
        (CAT_REPEATED, "Keeps making the same mistake"),
        (CAT_QUIZ, "Mistakes in a quiz"),
        (CAT_PREREQUISITE, "Missing background knowledge"),
        (CAT_ENGAGEMENT, "Low motivation or focus"),
        (CAT_TECHNICAL, "Technical problem"),
        (CAT_OTHER, "Other"),
    ]
    LOW, MEDIUM, HIGH = "low", "medium", "high"
    SEVERITY_CHOICES = [(LOW, "Low"), (MEDIUM, "Medium"), (HIGH, "High")]

    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True, related_name="events")
    attempt = models.ForeignKey(
        QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    concept = models.CharField(max_length=200, blank=True)
    note = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True, help_text="Set when the instructor marks it handled.")
    instructor_note = models.TextField(blank=True)
    client = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["enrollment", "type"])]

    def __str__(self):
        return f"{self.get_type_display()} — {self.enrollment}"


class PackSubmission(models.Model):
    """One result sent back from a copy-paste prompt (for AI apps without MCP).

    The nonce comes from the signed key inside the prompt, so each prompt can be submitted once.
    """

    LESSON = "lesson"
    QUIZ = "quiz"
    KIND_CHOICES = [(LESSON, "Lesson"), (QUIZ, "Quiz")]

    nonce = models.CharField(max_length=32, unique=True)
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="pack_submissions")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class ToolCall(models.Model):
    """Audit log of every MCP tool call (PRD §10), used for the tool-call success metric."""

    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, null=True, blank=True, related_name="tool_calls"
    )
    tool = models.CharField(max_length=60)
    client = models.CharField(max_length=30, blank=True)
    ok = models.BooleanField(default=True)
    error = models.CharField(max_length=300, blank=True)
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tool} ({'ok' if self.ok else 'error'})"
