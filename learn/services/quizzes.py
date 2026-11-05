"""Server-side quizzes (PRD §5): questions come from the server, answers go back,
grading happens here. The correct answer is never returned before the student answers.
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
    return list(quiz.questions.order_by("order", "id"))


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


def recompute_score(attempt: QuizAttempt) -> None:
    total = attempt.quiz.questions.count()
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
            events.record(attempt.enrollment, Event.QUIZ_FINISHED, lesson=attempt.quiz.lesson, client=client)
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
        result["instructions"] = (
            "Tell the student this result and their final score. Offer to review missed concepts. "
            "If they struggled with a concept, call report_stuck for it."
        )
    else:
        result["next_question"] = question_payload(nxt, number, len(questions))
        result["instructions"] = (
            "Tell the student this result (based only on this response) with the explanation, "
            "then ask the next question and wait. " + ASK_RULES
        )
    return result
