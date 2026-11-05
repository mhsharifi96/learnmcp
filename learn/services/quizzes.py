"""Quizzes.

Manual quizzes (PRD §5): questions come from the server, answers go back, grading happens here.
The correct answer is never returned before the student answers.

AI quizzes: the instructor only writes a prompt. The student's AI writes and grades the questions
one at a time and records each one with record_ai_answer, so the instructor still sees every
question, answer and score.
"""

from django.db import transaction
from django.utils import timezone

from learn.models import Answer, Event, Question, Quiz, QuizAttempt
from learn.services import ServiceError, events, grading
from learn.services.courses import enrollment_for_course

ASK_RULES = (
    "Ask the student this question exactly, show the options if any, then STOP and wait for their reply. "
    "Do not answer it, hint at the answer, or judge their reply yourself: pass their reply unchanged to "
    "submit_answer with this attempt_id and question_id."
)


def question_payload(question: Question, number: int, total: int) -> dict:
    data = {
        "question_id": question.id,
        "number": number,
        "total": total,
        "type": question.type,
        "prompt": question.prompt,
    }
    if question.type == Question.MCQ:
        data["options"] = [
            {"letter": grading.option_letter(i), "text": text} for i, text in enumerate(question.options_json)
        ]
        data["answer_format"] = "The student may reply with the letter or the option text."
    else:
        data["answer_format"] = "A short free-text answer."
    return data


def _questions(quiz) -> list[Question]:
    return list(quiz.manual_questions().order_by("order", "id"))


def _next_question(attempt, questions):
    answered = set(attempt.answers.values_list("question_id", flat=True))
    for number, q in enumerate(questions, start=1):
        if q.id not in answered:
            return number, q
    return None, None


def _score_summary(attempt, questions) -> dict:
    statuses = list(attempt.answers.values_list("status", flat=True))
    return {
        "correct": statuses.count(Answer.CORRECT),
        "incorrect": statuses.count(Answer.INCORRECT),
        "needs_review": statuses.count(Answer.NEEDS_REVIEW),
        "total": len(questions),
        "score_percent": attempt.score_percent,
    }


def mistakes(attempt) -> list[dict]:
    """The questions the student got wrong (or that need review), in question order."""
    answers = (
        attempt.answers.select_related("question")
        .exclude(status=Answer.CORRECT)
        .order_by("question__order", "question_id")
    )
    numbers = {} if attempt.quiz.is_ai else {q.id: n for n, q in enumerate(_questions(attempt.quiz), start=1)}
    out = []
    for a in answers:
        q = a.question
        out.append(
            {
                "number": numbers.get(q.id, q.order),
                "question": q.prompt,
                "student_answer": a.raw_answer,
                "correct_answer": grading.display_correct_answer(q),
                "result": a.status,
                "explanation": q.explanation,
                "concept": q.concept,
            }
        )
    return out


REPORT_RULES = (
    "The quiz is finished. Give the student a short report: their score, then go through each item in "
    "report.mistakes (question number, what they answered, the right answer and why). Then call "
    "submit_quiz_report with this attempt_id, a 2-4 sentence summary of how the quiz went and what the "
    "student misunderstood, and the list of concepts they should review. Offer to re-teach those concepts."
)


def _finish(attempt, *, client: str = "") -> dict:
    """Bookkeeping when an attempt ends: log it and report the mistakes to the instructor as a problem."""
    items = mistakes(attempt)
    events.record(attempt.enrollment, Event.QUIZ_FINISHED, lesson=attempt.quiz.lesson, attempt=attempt, client=client)
    wrong = [m for m in items if m["result"] == Answer.INCORRECT]
    if wrong:
        concepts = list(dict.fromkeys(m["concept"] for m in wrong if m["concept"]))
        total = attempt.quiz.ai_question_count if attempt.quiz.is_ai else len(_questions(attempt.quiz))
        share = len(wrong) / total if total else 0
        events.record(
            attempt.enrollment,
            Event.PROBLEM,
            lesson=attempt.quiz.lesson,
            attempt=attempt,
            category=Event.CAT_QUIZ,
            severity=Event.HIGH if share >= 0.5 else Event.MEDIUM if share >= 0.25 else Event.LOW,
            concept=", ".join(concepts) or attempt.quiz.title,
            note=f'{len(wrong)}/{total} wrong in "{attempt.quiz.title}": questions '
            + ", ".join(str(m["number"]) for m in wrong),
            client=client,
        )
    return {"mistakes": items, "all_correct": not items}


def submit_report(
    enrollment, attempt_id: int, summary: str, weak_concepts: list[str] | None = None, *, client: str = ""
) -> dict:
    summary = (summary or "").strip()
    if not summary:
        raise ServiceError("summary is empty. Write 2-4 sentences on how the quiz went and where the student went wrong.")
    attempt = (
        QuizAttempt.objects.select_related("quiz", "enrollment")
        .filter(pk=attempt_id, enrollment__student_id=enrollment.student_id)
        .first()
    )
    if attempt is None:
        raise ServiceError(f"Quiz attempt {attempt_id} was not found.")
    if not attempt.finished_at:
        raise ServiceError("This quiz is not finished yet. Finish all questions before sending the report.")
    concepts = [str(c).strip()[:120] for c in (weak_concepts or []) if str(c).strip()][:15]
    attempt.summary = summary[:4000]
    attempt.weak_concepts_json = concepts
    attempt.save(update_fields=["summary", "weak_concepts_json"])
    # Enrich the automatic quiz-mistakes problem with the AI's diagnosis.
    problem = attempt.events.filter(type=Event.PROBLEM, category=Event.CAT_QUIZ).first()
    if problem and concepts:
        problem.concept = ", ".join(concepts)[:200]
        problem.save(update_fields=["concept"])
    attempt.enrollment.touch()
    return {
        "recorded": True,
        "instructions": "Tell the student the report was sent to their instructor, then offer to review the weak concepts.",
    }


def recompute_score(attempt: QuizAttempt) -> None:
    quiz = attempt.quiz
    total = quiz.ai_question_count if quiz.is_ai else quiz.manual_questions().count()
    if attempt.finished_at and total:
        correct = attempt.answers.filter(status=Answer.CORRECT).count()
        attempt.score = correct / total
        attempt.save(update_fields=["score"])


def start(enrollment, quiz_id: int, *, client: str = "") -> dict:
    quiz = (
        Quiz.objects.select_related("course")
        .filter(pk=quiz_id, course__enrollments__student_id=enrollment.student_id)
        .first()
    )
    if quiz is None:
        raise ServiceError(f"Quiz {quiz_id} was not found in your classes. Call list_my_courses to see valid quiz ids.")
    target = enrollment_for_course(enrollment, quiz.course_id)
    if quiz.is_ai:
        return _start_ai(target, quiz, client=client)
    questions = _questions(quiz)
    if not questions:
        raise ServiceError("This quiz has no questions yet. Tell the student the instructor hasn't finished it.")

    attempt = QuizAttempt.objects.filter(enrollment=target, quiz=quiz, finished_at__isnull=True).first()
    resumed = attempt is not None
    if attempt is None:
        attempt = QuizAttempt.objects.create(enrollment=target, quiz=quiz)
        events.record(target, Event.QUIZ_STARTED, lesson=quiz.lesson, client=client)
    else:
        target.touch()

    number, question = _next_question(attempt, questions)
    return {
        "attempt_id": attempt.id,
        "quiz_title": quiz.title,
        "total_questions": len(questions),
        "resumed_unfinished_attempt": resumed,
        "question": question_payload(question, number, len(questions)),
        "instructions": ASK_RULES,
    }


def grade_and_next(enrollment, attempt_id: int, question_id: int, answer: str, *, client: str = "") -> dict:
    answer = (answer or "").strip()
    if not answer:
        raise ServiceError("The answer is empty. Ask the student for their answer, then call submit_answer again.")

    with transaction.atomic():
        attempt = (
            QuizAttempt.objects.select_for_update()
            .select_related("quiz", "enrollment")
            .filter(pk=attempt_id, enrollment__student_id=enrollment.student_id)
            .first()
        )
        if attempt is None:
            raise ServiceError(f"Quiz attempt {attempt_id} was not found. Call start_quiz to begin or resume a quiz.")
        if attempt.quiz.is_ai:
            raise ServiceError("This quiz is AI-generated. Record answers with record_ai_answer instead.")
        questions = _questions(attempt.quiz)
        if attempt.finished_at:
            raise ServiceError(
                f"This quiz attempt is already finished (score {attempt.score_percent}%). "
                "Call start_quiz again if the student wants to retake it."
            )
        question = next((q for q in questions if q.id == question_id), None)
        if question is None:
            raise ServiceError(f"Question {question_id} is not part of this quiz.")
        if attempt.answers.filter(question=question).exists():
            number, nxt = _next_question(attempt, questions)
            raise ServiceError(
                f"Question {question_id} was already answered. The next question is question_id={nxt.id}."
                if nxt
                else f"Question {question_id} was already answered."
            )

        status = grading.grade(question, answer)
        Answer.objects.create(attempt=attempt, question=question, raw_answer=answer[:5000], status=status)

        number, nxt = _next_question(attempt, questions)
        finished = nxt is None
        if finished:
            attempt.finished_at = timezone.now()
            correct = attempt.answers.filter(status=Answer.CORRECT).count()
            attempt.score = correct / len(questions)
            attempt.save(update_fields=["finished_at", "score"])
            report = _finish(attempt, client=client)
        else:
            attempt.enrollment.touch()

    messages = {
        Answer.CORRECT: "Correct.",
        Answer.INCORRECT: "Not quite.",
        Answer.NEEDS_REVIEW: "The answer did not match the expected answers exactly, so the instructor will review it.",
    }
    result = {
        "result": status,
        "message": messages[status],
        "correct_answer": grading.display_correct_answer(question),
        "explanation": question.explanation,
        "finished": finished,
    }
    if finished:
        result["score"] = _score_summary(attempt, questions)
        result["report"] = report
        result["instructions"] = "Tell the student this result first. " + REPORT_RULES
    else:
        result["next_question"] = question_payload(nxt, number, len(questions))
        result["instructions"] = (
            "Tell the student this result (based only on this response) with the explanation, "
            "then ask the next question and wait. " + ASK_RULES
        )
    return result


# --------------------------------------------------------------------------- AI-generated quizzes

AI_RULES = (
    "This quiz is written by YOU from the instructor's prompt below. "
    "Write ONE question at a time that fits the prompt and the lesson (multiple choice with options A, B, C… "
    "or a short answer). Ask it, then STOP and wait for the student's reply; never answer it for them or hint. "
    "Then judge the reply fairly (accept small spelling slips only if the prompt allows it) and call "
    "record_ai_answer with this attempt_id, the exact question you asked, the options (if any), the correct "
    "answer, the student's reply unchanged, whether it is correct, a one-line explanation and the concept. "
    "Tell the student the result, then ask the next question. Do not repeat questions already asked."
)


def _lesson_context(lesson) -> dict | None:
    if lesson is None:
        return None
    return {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "objectives": lesson.objectives_list,
        "lesson_prompt": lesson.brief or None,
        "content": lesson.content or None,
    }


def _start_ai(target, quiz, *, client: str = "") -> dict:
    attempt = QuizAttempt.objects.filter(enrollment=target, quiz=quiz, finished_at__isnull=True).first()
    resumed = attempt is not None
    if attempt is None:
        attempt = QuizAttempt.objects.create(enrollment=target, quiz=quiz)
        events.record(target, Event.QUIZ_STARTED, lesson=quiz.lesson, client=client)
    else:
        target.touch()
    asked = list(attempt.generated_questions.order_by("order", "id").values_list("prompt", flat=True))
    return {
        "attempt_id": attempt.id,
        "quiz_title": quiz.title,
        "mode": "ai_generated",
        "total_questions": quiz.ai_question_count,
        "questions_answered": len(asked),
        "next_question_number": len(asked) + 1,
        "resumed_unfinished_attempt": resumed,
        "instructor_prompt": quiz.prompt,
        "lesson": _lesson_context(quiz.lesson),
        "already_asked": asked,
        "instructions": AI_RULES,
    }


def record_ai_answer(
    enrollment,
    attempt_id: int,
    question: str,
    correct_answer: str,
    student_answer: str,
    is_correct: bool,
    *,
    options: list[str] | None = None,
    explanation: str = "",
    concept: str = "",
    client: str = "",
) -> dict:
    question = (question or "").strip()
    student_answer = (student_answer or "").strip()
    if not question:
        raise ServiceError("question is empty. Pass the exact question you asked the student.")
    if not student_answer:
        raise ServiceError("student_answer is empty. Ask the student for their answer first.")
    options = [str(o).strip() for o in (options or []) if str(o).strip()]

    with transaction.atomic():
        attempt = (
            QuizAttempt.objects.select_for_update()
            .select_related("quiz", "enrollment")
            .filter(pk=attempt_id, enrollment__student_id=enrollment.student_id)
            .first()
        )
        if attempt is None:
            raise ServiceError(f"Quiz attempt {attempt_id} was not found. Call start_quiz to begin or resume a quiz.")
        quiz = attempt.quiz
        if not quiz.is_ai:
            raise ServiceError("This quiz has instructor-written questions. Use submit_answer instead.")
        if attempt.finished_at:
            raise ServiceError(
                f"This quiz attempt is already finished (score {attempt.score_percent}%). "
                "Call start_quiz again if the student wants to retake it."
            )
        total = quiz.ai_question_count
        number = attempt.generated_questions.count() + 1
        q = Question.objects.create(
            quiz=quiz,
            attempt=attempt,
            order=number,
            type=Question.MCQ if len(options) >= 2 else Question.SHORT,
            prompt=question[:5000],
            options_json=options if len(options) >= 2 else [],
            correct_answer=(correct_answer or "").strip()[:500],
            explanation=(explanation or "").strip()[:2000],
            concept=(concept or "").strip()[:120],
        )
        status = Answer.CORRECT if is_correct else Answer.INCORRECT
        Answer.objects.create(attempt=attempt, question=q, raw_answer=student_answer[:5000], status=status)

        finished = number >= total
        if finished:
            attempt.finished_at = timezone.now()
            correct = attempt.answers.filter(status=Answer.CORRECT).count()
            attempt.score = min(1.0, correct / total)
            attempt.save(update_fields=["finished_at", "score"])
            report = _finish(attempt, client=client)
        else:
            attempt.enrollment.touch()

    result = {"recorded": True, "result": status, "question_number": number, "total": total, "finished": finished}
    if finished:
        correct = attempt.answers.filter(status=Answer.CORRECT).count()
        result["score"] = {"correct": correct, "total": total, "score_percent": attempt.score_percent}
        result["report"] = report
        result["instructions"] = REPORT_RULES
    else:
        result["instructions"] = (
            f"Tell the student the result, then write and ask question {number + 1} of {total}. " + AI_RULES
        )
    return result
