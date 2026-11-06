"""A student's own learning history, in plain terms (for the "My classes" page).

The raw Event log is written for instructors and tooling. Here it becomes a short timeline:
lessons studied (repeat opens on one day collapsed), lesson feedback, finished quizzes with
their score, and problems the AI reported. Bookkeeping events are left out.
"""

from django.db.models import Prefetch

from learn.models import Answer, Event, Lesson, Quiz, QuizAttempt
from learn.services.courses import LESSON_NOT_STARTED, LESSON_QUIZ_DONE, LESSON_STARTED, lesson_statuses

APP_NAMES = {
    "claude": "Claude",
    "chatgpt": "ChatGPT",
    "gemini": "Gemini",
    "deepseek": "DeepSeek",
    "copilot": "Copilot",
    "cursor": "Cursor",
}


def app_label(client: str) -> dict:
    """'prompt:gemini' -> {"name": "Gemini", "via": "prompt"}; 'claude' -> {"name": "Claude", "via": "mcp"}."""
    client = (client or "").strip().lower()
    via = "mcp"
    if client.startswith("prompt"):
        via = "prompt"
        client = client.partition(":")[2]
    name = next((v for k, v in APP_NAMES.items() if k in client), client.title() if client else "")
    return {"name": name, "via": via}


def feedback_fields(ev) -> dict:
    """Split a lesson-feedback event ("Understood 3/5. summary") into its parts."""
    understood, note = None, ev.note
    if ev.note.startswith("Understood ") and "/5" in ev.note:
        try:
            understood = int(ev.note.split()[1].split("/")[0])
            note = ev.note.split(". ", 1)[1] if ". " in ev.note else ""
        except (IndexError, ValueError):
            understood = None
    return {"understood": understood, "difficult": [c.strip() for c in ev.concept.split(",") if c.strip()], "note": note}


def _iso(dt):
    return dt.isoformat() if dt else None


def timeline(enrollment, limit: int = 60) -> list[dict]:
    items: list[dict] = []
    seen_lesson_days: set[tuple] = set()
    for ev in enrollment.events.select_related("lesson", "attempt").order_by("-created_at"):
        if ev.type == Event.LESSON_STARTED:
            key = (ev.lesson_id, ev.created_at.date())
            if key in seen_lesson_days:
                continue
            seen_lesson_days.add(key)
            items.append(
                {
                    "type": "lesson",
                    "at": _iso(ev.created_at),
                    "title": ev.lesson.title if ev.lesson else "",
                    "app": app_label(ev.client),
                }
            )
        elif ev.type == Event.LESSON_FEEDBACK:
            items.append(
                {
                    "type": "feedback",
                    "at": _iso(ev.created_at),
                    "title": ev.lesson.title if ev.lesson else "",
                    **feedback_fields(ev),
                    "app": app_label(ev.client),
                }
            )
        elif ev.type == Event.PROBLEM and ev.category != Event.CAT_QUIZ:
            # Quiz mistakes are already visible on the quiz entry itself.
            items.append(
                {
                    "type": "problem",
                    "at": _iso(ev.created_at),
                    "title": ev.concept or (ev.lesson.title if ev.lesson else ""),
                    "lesson": ev.lesson.title if ev.lesson else None,
                    "note": ev.note,
                    "category": ev.category,
                    "resolved": ev.resolved_at is not None,
                    "instructor_note": ev.instructor_note,
                }
            )

    attempts = (
        QuizAttempt.objects.filter(enrollment=enrollment)
        .select_related("quiz", "quiz__lesson")
        .prefetch_related("answers__question")
    )
    clients = dict(
        enrollment.events.filter(type=Event.QUIZ_FINISHED, attempt__isnull=False).values_list("attempt_id", "client")
    )
    for a in attempts:
        answers = sorted(a.answers.all(), key=lambda x: (x.question.order, x.question_id))
        statuses = [x.status for x in answers]
        items.append(
            {
                "type": "quiz",
                "at": _iso(a.finished_at or a.started_at),
                "attempt_id": a.id,
                "title": a.quiz.title,
                "lesson": a.quiz.lesson.title if a.quiz.lesson else None,
                "finished": a.finished_at is not None,
                "score_percent": a.score_percent,
                "correct": statuses.count(Answer.CORRECT),
                "needs_review": statuses.count(Answer.NEEDS_REVIEW),
                "total": a.quiz.ai_question_count if a.quiz.is_ai else len(a.quiz.manual_questions()),
                "answered": len(answers),
                "summary": a.summary,
                "weak_concepts": a.weak_concepts_json,
                "app": app_label(clients.get(a.id, "")),
                "answers": [
                    {"question": x.question.prompt, "answer": x.raw_answer, "status": x.status} for x in answers
                ],
            }
        )
    items.sort(key=lambda i: i["at"] or "", reverse=True)
    return items[:limit]


def progress(enrollment) -> dict:
    statuses = lesson_statuses([enrollment.id])
    best: dict[int, int] = {}
    for quiz_id, score in QuizAttempt.objects.filter(enrollment=enrollment, finished_at__isnull=False).values_list(
        "quiz_id", "score"
    ):
        best[quiz_id] = max(best.get(quiz_id, 0), round((score or 0) * 100))
    lessons = []
    published = (
        Lesson.objects.published().filter(course=enrollment.course)
        .prefetch_related(Prefetch("quizzes", queryset=Quiz.objects.published()))
        .order_by("order", "id")
    )
    for lesson in published:
        quiz_scores = [best[q.id] for q in lesson.quizzes.all() if q.id in best]
        lessons.append(
            {
                "id": lesson.id,
                "order": lesson.order,
                "title": lesson.title,
                "kind": lesson.kind,
                "status": statuses.get(lesson.id, LESSON_NOT_STARTED),
                "best_score_percent": max(quiz_scores) if quiz_scores else None,
            }
        )
    scores = list(best.values())
    return {
        "lessons_total": len(lessons),
        "lessons_started": sum(1 for l in lessons if l["status"] in (LESSON_STARTED, LESSON_QUIZ_DONE)),
        "lessons_done": sum(1 for l in lessons if l["status"] == LESSON_QUIZ_DONE),
        "quizzes_done": len(scores),
        "average_score_percent": round(sum(scores) / len(scores)) if scores else None,
        "lessons": lessons,
        "next_lesson": next(
            ({"id": l["id"], "title": l["title"]} for l in lessons if l["status"] != LESSON_QUIZ_DONE), None
        ),
    }
