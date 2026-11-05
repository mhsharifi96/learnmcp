import json

import pytest

from learn.models import Answer, Event, Question, QuizAttempt
from learn.services import ServiceError, enrollments, grading, quizzes
from tests.conftest import make_course, make_instructor


def q(**kw):
    defaults = dict(type="mcq", options_json=["Paris", "Rome", "Madrid"], correct_answer="A", accepted_answers_json=[])
    defaults.update(kw)
    return Question(**defaults)


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("A", "correct"), ("a", "correct"), ("(a)", "correct"), ("A)", "correct"), ("a.", "correct"),
        ("paris", "correct"), ("  PARIS! ", "correct"), ("A) Paris", "correct"), ("option a", "correct"),
        ("B", "incorrect"), ("Rome", "incorrect"), ("E", "incorrect"), ("no idea", "incorrect"), ("", "incorrect"),
    ],
)
def test_mcq_grading(answer, expected):
    assert grading.grade(q(), answer) == expected


def test_mcq_correct_answer_given_as_text():
    assert grading.grade(q(correct_answer="Rome"), "b") == "correct"
    assert grading.grade(q(correct_answer="Rome"), "a") == "incorrect"


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("H2O", "correct"), ("h2o", "correct"), ("H 2 O", "correct"), ("h2o.", "correct"),
        ("Wasser", "needs_review"), ("Café", "correct"), ("cafe", "correct"),
    ],
)
def test_short_grading_normalises(answer, expected):
    question = Question(type="short", correct_answer="H2O", accepted_answers_json=["Café"])
    assert grading.grade(question, answer) == expected


def test_question_clean_rejects_bad_mcq(db):
    from django.core.exceptions import ValidationError

    with pytest.raises(ValidationError):
        q(options_json=["only one"]).clean()
    with pytest.raises(ValidationError):
        q(correct_answer="Berlin").clean()


def _no_answer_leak(payload, quiz):
    text = json.dumps(payload).lower()
    for question in quiz.questions.all():
        assert "correct_answer" not in text
        for accepted in question.accepted_answers_json:
            assert accepted.lower() not in text


def test_start_quiz_orders_questions_and_hides_answers(enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    out = quizzes.start(enrollment, quiz.id)
    assert out["question"]["number"] == 1
    assert out["question"]["prompt"] == "Type of 3.5?"  # order=1 comes first despite later id
    assert [o["letter"] for o in out["question"]["options"]] == ["A", "B", "C"]
    _no_answer_leak(out, quiz)
    assert Event.objects.filter(enrollment=enrollment, type=Event.QUIZ_STARTED).count() == 1


def test_full_quiz_flow_scores_and_finishes(enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    start = quizzes.start(enrollment, quiz.id)
    r1 = quizzes.grade_and_next(enrollment, start["attempt_id"], start["question"]["question_id"], "float")
    assert r1["result"] == "correct" and not r1["finished"]
    _no_answer_leak(r1["next_question"], quiz)
    r2 = quizzes.grade_and_next(enrollment, start["attempt_id"], r1["next_question"]["question_id"], "len")
    assert r2["result"] == "needs_review" and r2["finished"]
    assert r2["score"] == {"correct": 1, "incorrect": 0, "needs_review": 1, "total": 2, "score_percent": 50}

    attempt = QuizAttempt.objects.get(pk=start["attempt_id"])
    assert attempt.finished_at and attempt.score == 0.5

    # Instructor marks the short answer correct -> score recomputed.
    Answer.objects.filter(attempt=attempt, status=Answer.NEEDS_REVIEW).update(status=Answer.CORRECT)
    quizzes.recompute_score(attempt)
    attempt.refresh_from_db()
    assert attempt.score == 1.0

    with pytest.raises(ServiceError, match="already finished"):
        quizzes.grade_and_next(enrollment, attempt.id, r1["next_question"]["question_id"], "type")


def test_resume_and_double_answer(enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    first = quizzes.start(enrollment, quiz.id)
    qid = first["question"]["question_id"]
    quizzes.grade_and_next(enrollment, first["attempt_id"], qid, "B")
    with pytest.raises(ServiceError, match="already answered"):
        quizzes.grade_and_next(enrollment, first["attempt_id"], qid, "A")
    resumed = quizzes.start(enrollment, quiz.id)
    assert resumed["attempt_id"] == first["attempt_id"]
    assert resumed["resumed_unfinished_attempt"] is True
    assert resumed["question"]["number"] == 2


def test_empty_answer_rejected(enrolled, course_setup):
    enrollment, _ = enrolled
    start = quizzes.start(enrollment, course_setup[3].id)
    with pytest.raises(ServiceError, match="empty"):
        quizzes.grade_and_next(enrollment, start["attempt_id"], start["question"]["question_id"], "   ")


def test_student_cannot_touch_other_class_or_attempt(enrolled, course_setup, other_instructor):
    enrollment, _ = enrolled
    other_course, _, _, other_quiz = make_course(other_instructor, "Secret class")
    with pytest.raises(ServiceError, match="not found"):
        quizzes.start(enrollment, other_quiz.id)

    intruder, _ = enrollments.join(other_course, name="Eve", email="eve@example.com")
    attempt = quizzes.start(enrollment, course_setup[3].id)
    with pytest.raises(ServiceError, match="not found"):
        quizzes.grade_and_next(intruder, attempt["attempt_id"], attempt["question"]["question_id"], "B")


def test_ai_quiz_and_lesson_validation(course_setup):
    import pytest as _pytest
    from django.core.exceptions import ValidationError

    from learn.models import Lesson, Quiz

    course = course_setup[0]
    with _pytest.raises(ValidationError):
        Quiz(course=course, title="x", mode=Quiz.AI, prompt="").clean()
    Quiz(course=course, title="x", mode=Quiz.AI, prompt="5 questions", ai_question_count=5).clean()
    with _pytest.raises(ValidationError):
        Lesson(course=course, title="empty").clean()
    Lesson(course=course, title="brief only", brief="Teach greetings").clean()


def test_build_english_course(course_setup):
    from django.core.management import call_command

    from learn.models import Quiz

    course = course_setup[0]
    call_command("build_english_course", "--join-code", course.join_code)
    course.refresh_from_db()
    lessons = list(course.lessons.order_by("order"))
    assert len(lessons) == 13 and lessons[0].title.startswith("Placement")
    assert all(not lesson.content and lesson.brief for lesson in lessons)
    assert course.quizzes.count() == 13 and not course.quizzes.exclude(mode=Quiz.AI).exists()
