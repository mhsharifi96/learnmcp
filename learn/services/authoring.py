"""Build lessons and quizzes with the instructor's own AI (ChatGPT, Claude, Gemini…).

1. The instructor writes a goal. build_prompt() turns it into a prompt that describes this
   class and the exact JSON shape the site accepts.
2. The instructor pastes the prompt into their AI and copies the JSON it returns.
3. import_json() validates everything and creates it as drafts, all or nothing. Drafts stay
   hidden from students until the instructor reviews and publishes them.
"""

import json

from django.core.exceptions import ValidationError
from django.db import transaction

from learn.models import Course, Lesson, Question, Quiz
from learn.services import ServiceError, lesson_kinds

TARGET_LESSONS = "lessons"
TARGET_QUIZZES = "quizzes"
TARGETS = (TARGET_LESSONS, TARGET_QUIZZES)

MAX_GOAL = 4000
MAX_IMPORT = 1_000_000
MAX_LESSONS = 30
MAX_QUIZZES = 40
MAX_QUESTIONS = 50

KIND_HINTS = {
    lesson_kinds.GENERAL: "any subject, taught step by step",
    "grammar": "a grammar rule with controlled and free practice",
    "vocabulary": "a set of words with meaning, examples and recall",
    "translation": "Persian-to-English sentence translation practice",
    "speaking": "spoken answers to questions, with feedback",
    "conversation": "a real-life role-play",
}

QUESTION_SHAPE = """{
          "type": "mcq" or "short",
          "prompt": "the question",
          "options": ["option text", ...],          // mcq only, 2-6 options, no letters inside
          "correct_answer": "B",                    // mcq: the option letter; short: the model answer
          "accepted_answers": ["other ok answer"],  // short only, optional
          "explanation": "one line shown after answering",
          "concept": "the concept tested (2-4 words)"
        }"""

QUIZ_SHAPE = """{
      "title": "quiz title",
      "mode": "manual" or "ai",
      // manual: you write the questions below; the server grades them.
      // ai: the student's AI writes the questions live from "prompt"; leave "questions" empty.
      "prompt": "ai mode only: what to ask, level, focus, question types",
      "question_count": 8,                         // ai mode only, 1-50
      "questions": [ QUESTION ]                     // manual mode only, 3-15 questions
    }"""


def _kinds_text() -> str:
    return "\n".join(f'  - "{k}": {KIND_HINTS.get(k, v["label"])}' for k, v in lesson_kinds.KINDS.items())


def _existing_lessons(course: Course) -> str:
    rows = [f'  - lesson_id {l.id}: {l.order}. "{l.title}"' for l in course.lessons.order_by("order", "id")]
    return "\n".join(rows) or "  (none yet)"


def build_prompt(course: Course, goal: str, target: str = TARGET_LESSONS) -> str:
    goal = (goal or "").strip()
    if not goal:
        raise ServiceError("Write your goal first.")
    if len(goal) > MAX_GOAL:
        raise ServiceError("The goal is too long. Keep it under 4000 characters.")
    if target not in TARGETS:
        target = TARGET_LESSONS

    if target == TARGET_LESSONS:
        task = (
            "Design the lessons for my goal below, each with its quizzes. Split the material into small lessons "
            "(one main idea each, 15-30 minutes of study), in a sensible order. Give most lessons one quiz."
        )
        shape = f"""{{
  "lessons": [
    {{
      "title": "short lesson title",
      "kind": "general",
      "objectives": ["what the student can do after the lesson", ...],
      "brief": "the lesson prompt: topic, level, scope, key points, examples to use (3-8 lines)",
      "content": "",
      "teaching_notes": "tone, common mistakes to watch for, how to check understanding",
      "quizzes": [ QUIZ ]
    }}
  ]
}}"""
    else:
        task = (
            "Write quizzes for my goal below. Attach each quiz to one of my existing lessons with "
            '"lesson_id" (from the list), or use null for a class-wide quiz.'
        )
        shape = """{
  "quizzes": [
    QUIZ_WITH "lesson_id": <number from the list, or null>
  ]
}"""

    return f"""You are helping me, a teacher, prepare material for my class on an AI tutoring site.
Students study each lesson with their own AI tutor: the "brief" and "teaching_notes" you write are
instructions for that tutor, so make them concrete. Quizzes check the lesson.

MY CLASS: "{course.title}"
{course.description.strip() or ""}

EXISTING LESSONS:
{_existing_lessons(course)}

TASK: {task}

MY GOAL:
{goal}

RULES
- Write all content in the language of my goal (students read it), except material that must be in
  another language (for example English sentences in an English class).
- Lesson "kind" is one of:
{_kinds_text()}
- "content" is optional: leave it "" and the student's AI builds the lesson from "brief". Fill it only
  if a fixed text is needed (a reading passage, a word list).
- Prefer "manual" quizzes for facts, rules and vocabulary (exact answers, graded by the server) and
  "ai" quizzes for open practice. Manual questions must have exactly one correct answer.
- Do not repeat my existing lessons.

OUTPUT: reply with ONLY one JSON code block, valid JSON (no comments, no trailing commas), in exactly
this shape, then one short line telling me to copy it. Nothing else.

{shape}

QUIZ =
    {QUIZ_SHAPE}

QUESTION =
        {QUESTION_SHAPE}
"""


# --------------------------------------------------------------------------- import


class _Errors:
    def __init__(self):
        self.items: list[str] = []

    def add(self, where: str, msg) -> None:
        self.items.append(f"{where}: {msg}")


def _s(value, limit: int) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        value = "\n".join(str(v) for v in value)
    return str(value).strip()[:limit]


def _str_list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()]


def _validation_text(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return "; ".join(f"{k}: {' '.join(v)}" for k, v in exc.message_dict.items())
    return " ".join(exc.messages)


def _lesson_from(course: Course, raw: dict, order: int, where: str, errs: _Errors) -> Lesson | None:
    if not isinstance(raw, dict):
        errs.add(where, "must be an object")
        return None
    kind = _s(raw.get("kind"), 20) or lesson_kinds.GENERAL
    if kind not in lesson_kinds.KINDS:
        kind = lesson_kinds.GENERAL
    objectives = raw.get("objectives")
    lesson = Lesson(
        course=course,
        order=order,
        title=_s(raw.get("title"), 200),
        kind=kind,
        objectives="\n".join(_str_list(objectives)) if isinstance(objectives, list) else _s(objectives, 5000),
        brief=_s(raw.get("brief"), 20000),
        content=_s(raw.get("content"), 100000),
        teaching_notes=_s(raw.get("teaching_notes"), 20000),
        draft=True,
    )
    try:
        lesson.full_clean(exclude=["course"])
    except ValidationError as exc:
        errs.add(f'{where} "{lesson.title or "?"}"', _validation_text(exc))
        return None
    return lesson


def _question_from(raw, n: int, where: str, errs: _Errors) -> Question | None:
    if not isinstance(raw, dict):
        errs.add(where, "must be an object")
        return None
    options = _str_list(raw.get("options"))
    qtype = Question.MCQ if (_s(raw.get("type"), 10).lower() == Question.MCQ or len(options) >= 2) else Question.SHORT
    if qtype == Question.SHORT:
        options = []
    q = Question(
        order=n,
        type=qtype,
        prompt=_s(raw.get("prompt") or raw.get("q") or raw.get("question"), 5000),
        options_json=options,
        correct_answer=_s(raw.get("correct_answer") or raw.get("correct") or raw.get("answer"), 500),
        accepted_answers_json=_str_list(raw.get("accepted_answers")),
        explanation=_s(raw.get("explanation"), 2000),
        concept=_s(raw.get("concept"), 120),
    )
    try:
        q.full_clean(exclude=["quiz", "attempt"])
    except ValidationError as exc:
        errs.add(where, _validation_text(exc))
        return None
    return q


def _quiz_from(course: Course, raw, where: str, errs: _Errors, lessons_by_id: dict[int, Lesson]):
    """Returns (quiz, questions, lesson_ref). lesson_ref is an existing lesson id or None."""
    if not isinstance(raw, dict):
        errs.add(where, "must be an object")
        return None
    mode = Quiz.AI if _s(raw.get("mode"), 10).lower() == Quiz.AI else Quiz.MANUAL
    try:
        count = int(raw.get("question_count") or raw.get("ai_question_count") or 5)
    except (TypeError, ValueError):
        count = 5
    quiz = Quiz(
        course=course,
        title=_s(raw.get("title"), 200),
        mode=mode,
        prompt=_s(raw.get("prompt"), 20000) if mode == Quiz.AI else "",
        ai_question_count=min(50, max(1, count)),
        draft=True,
    )
    label = f'{where} "{quiz.title or "?"}"'
    if not quiz.title:
        errs.add(label, "title: This field cannot be blank.")
    lesson_ref = None
    if "lesson_id" in raw and raw["lesson_id"] not in (None, "", 0):
        try:
            lesson_ref = int(raw["lesson_id"])
        except (TypeError, ValueError):
            lesson_ref = -1
        if lesson_ref not in lessons_by_id:
            errs.add(label, f"lesson_id {raw['lesson_id']} is not a lesson of this class.")
    if mode == Quiz.AI and not quiz.prompt:
        errs.add(label, "prompt: an ai quiz needs a prompt.")
    questions = []
    if mode == Quiz.MANUAL:
        raw_qs = raw.get("questions")
        if not isinstance(raw_qs, list) or not raw_qs:
            errs.add(label, "a manual quiz needs at least one question.")
            raw_qs = []
        if len(raw_qs) > MAX_QUESTIONS:
            errs.add(label, f"at most {MAX_QUESTIONS} questions.")
            raw_qs = raw_qs[:MAX_QUESTIONS]
        for n, rq in enumerate(raw_qs, start=1):
            q = _question_from(rq, n, f"{label} question {n}", errs)
            if q is not None:
                questions.append(q)
    return quiz, questions, lesson_ref


def parse_import(raw: str) -> dict:
    """Accepts the AI's reply: a JSON code block, maybe with text around it."""
    raw = (raw or "").strip()
    if not raw:
        raise ServiceError("Paste the JSON your AI made.")
    if len(raw) > MAX_IMPORT:
        raise ServiceError("The text is too long. Import fewer lessons at once.")
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start : end + 1]) if 0 <= start < end else None
    except ValueError as exc:
        raise ServiceError(
            f"The text is not valid JSON ({exc.msg}, line {exc.lineno}). Copy the whole code block, or ask your AI "
            "to send it again as valid JSON."
        ) from exc
    if not isinstance(data, dict):
        raise ServiceError("The text is not valid JSON. Copy the whole code block your AI made.")
    if isinstance(data.get("lessons"), dict):
        data["lessons"] = [data["lessons"]]
    if not isinstance(data.get("lessons", []), list) or not isinstance(data.get("quizzes", []), list):
        raise ServiceError('"lessons" and "quizzes" must be lists.')
    if not data.get("lessons") and not data.get("quizzes"):
        raise ServiceError('The JSON has no "lessons" or "quizzes".')
    return data


def import_json(course: Course, raw: str) -> dict:
    """Validate everything first, then create it all as drafts in one transaction."""
    data = parse_import(raw)

    raw_lessons = data.get("lessons") or []
    raw_quizzes = data.get("quizzes") or []
    if len(raw_lessons) > MAX_LESSONS:
        raise ServiceError(f"Too many lessons at once (at most {MAX_LESSONS}).")
    errs = _Errors()
    lessons_by_id = {l.id: l for l in course.lessons.all()}
    next_order = max([l.order for l in lessons_by_id.values()] or [0]) + 1

    planned: list[tuple[Lesson, list]] = []
    for i, rl in enumerate(raw_lessons, start=1):
        lesson = _lesson_from(course, rl, next_order + i - 1, f"lesson {i}", errs)
        lesson_quizzes = []
        for j, rq in enumerate((rl.get("quizzes") or []) if isinstance(rl, dict) else [], start=1):
            parsed = _quiz_from(course, rq, f"lesson {i} quiz {j}", errs, lessons_by_id)
            if parsed:
                lesson_quizzes.append(parsed)
        if lesson is not None:
            planned.append((lesson, lesson_quizzes))

    loose = []
    for j, rq in enumerate(raw_quizzes, start=1):
        parsed = _quiz_from(course, rq, f"quiz {j}", errs, lessons_by_id)
        if parsed:
            loose.append(parsed)

    quiz_total = sum(len(qs) for _, qs in planned) + len(loose)
    if quiz_total > MAX_QUIZZES:
        errs.add("quizzes", f"too many quizzes at once (at most {MAX_QUIZZES}).")
    if errs.items:
        raise ServiceError("Nothing was imported. Fix these and try again:\n" + "\n".join(errs.items[:30]))

    def save_quiz(quiz: Quiz, questions: list[Question], lesson: Lesson | None) -> None:
        quiz.lesson = lesson
        quiz.save()
        for q in questions:
            q.quiz = quiz
        Question.objects.bulk_create(questions)

    with transaction.atomic():
        for lesson, lesson_quizzes in planned:
            lesson.save()
            for quiz, questions, ref in lesson_quizzes:
                save_quiz(quiz, questions, lessons_by_id.get(ref) if ref else lesson)
        for quiz, questions, ref in loose:
            save_quiz(quiz, questions, lessons_by_id.get(ref) if ref else None)

    return {"lessons": len(planned), "quizzes": quiz_total}


def publish_all(course: Course) -> dict:
    with transaction.atomic():
        lessons = course.lessons.filter(draft=True).update(draft=False)
        quizzes = course.quizzes.filter(draft=True).update(draft=False)
    return {"lessons": lessons, "quizzes": quizzes}
