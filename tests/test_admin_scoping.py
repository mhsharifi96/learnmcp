import pytest
from django.urls import reverse

from learn.models import Answer, Course, Lesson, Quiz
from learn.services import enrollments, quizzes
from tests.conftest import make_course


@pytest.fixture
def two_classes(instructor, other_instructor):
    mine = make_course(instructor, "Alice class")
    theirs = make_course(other_instructor, "Bob class")
    return mine, theirs


def login(client, instructor):
    client.force_login(instructor.user)
    return client


def test_changelists_only_show_own_data(client, instructor, two_classes):
    login(client, instructor)
    for name in ["course", "lesson", "quiz"]:
        resp = client.get(reverse(f"admin:learn_{name}_changelist"))
        assert resp.status_code == 200, name
        body = resp.content.decode()
        assert "Bob class" not in body
    body = client.get(reverse("admin:learn_course_changelist")).content.decode()
    assert "Alice class" in body


def test_cannot_open_or_edit_other_instructors_objects(client, instructor, two_classes):
    login(client, instructor)
    (_, _, _, _), (their_course, their_lesson, _, their_quiz) = two_classes
    for url in [
        reverse("admin:learn_course_change", args=[their_course.pk]),
        reverse("admin:learn_lesson_change", args=[their_lesson.pk]),
        reverse("admin:learn_quiz_change", args=[their_quiz.pk]),
    ]:
        resp = client.get(url)
        assert resp.status_code == 302 and "Bob" not in resp.content.decode()  # admin redirects: "doesn't exist"
    resp = client.post(reverse("admin:learn_course_delete", args=[their_course.pk]), {"post": "yes"})
    assert Course.objects.filter(pk=their_course.pk).exists()
    assert client.get(reverse("admin:learn_course_dashboard", args=[their_course.pk])).status_code == 404


def test_fk_choices_are_scoped(client, instructor, two_classes):
    login(client, instructor)
    body = client.get(reverse("admin:learn_lesson_add")).content.decode()
    assert "Alice class" in body and "Bob class" not in body
    (my_course, *_), (their_course, *_ ) = two_classes
    resp = client.post(
        reverse("admin:learn_lesson_add"),
        {"course": their_course.pk, "order": 1, "title": "Injected", "content": "x"},
    )
    assert resp.status_code == 200  # form error: invalid choice
    assert not Lesson.objects.filter(title="Injected").exists()


def test_new_course_belongs_to_creator(client, instructor, other_instructor):
    login(client, instructor)
    data = {
        "title": "Brand new", "description": "",
        "lessons-TOTAL_FORMS": 0, "lessons-INITIAL_FORMS": 0,
        "quizzes-TOTAL_FORMS": 0, "quizzes-INITIAL_FORMS": 0,
    }
    resp = client.post(reverse("admin:learn_course_add"), data)
    assert resp.status_code == 302, resp.content.decode()[:2000]
    course = Course.objects.get(title="Brand new")
    assert course.instructor == instructor and len(course.join_code) == 8


def test_dashboard_shows_scores_stuck_and_inactive(client, instructor, course_setup):
    course, lesson1, _, quiz = course_setup
    enr, _ = enrollments.join(course, name="Sam", email="sam@example.com")
    idle, _ = enrollments.join(course, name="Idle Ivy", email="ivy@example.com")
    start = quizzes.start(enr, quiz.id)
    r = quizzes.grade_and_next(enr, start["attempt_id"], start["question"]["question_id"], "A")
    quizzes.grade_and_next(enr, start["attempt_id"], r["next_question"]["question_id"], "type")
    enrollments.report_stuck(enr, lesson_id=lesson1.id, concept="Floats", note="decimals?")

    login(client, instructor)
    resp = client.get(reverse("admin:learn_course_dashboard", args=[course.pk]))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert "Sam" in body and "Idle Ivy" in body
    assert "50%" in body  # one of two correct
    assert "floats" in body  # stuck concept (normalised to lowercase)
    assert "inactive" in body  # Ivy never did anything
    assert "Type of 3.5?" in body  # most-missed question
    ctx = resp.context
    assert ctx["inactive_count"] == 1 and ctx["student_count"] == 2


def test_review_action_updates_score(client, instructor, course_setup):
    course, _, _, quiz = course_setup
    enr, _ = enrollments.join(course, name="Sam", email="sam@example.com")
    start = quizzes.start(enr, quiz.id)
    r = quizzes.grade_and_next(enr, start["attempt_id"], start["question"]["question_id"], "B")
    quizzes.grade_and_next(enr, start["attempt_id"], r["next_question"]["question_id"], "it is type of course")
    answer = Answer.objects.get(status=Answer.NEEDS_REVIEW)

    login(client, instructor)
    resp = client.post(
        reverse("admin:learn_answer_changelist"),
        {"action": "mark_correct", "_selected_action": [answer.pk]},
    )
    assert resp.status_code == 302
    answer.attempt.refresh_from_db()
    assert answer.attempt.score == 1.0


def test_instructor_cannot_see_other_students(client, instructor, two_classes):
    _, (their_course, *_) = two_classes
    enrollments.join(their_course, name="Hidden Hannah", email="h@example.com")
    login(client, instructor)
    for name in ["enrollment", "event", "quizattempt", "answer"]:
        body = client.get(reverse(f"admin:learn_{name}_changelist")).content.decode()
        assert "Hidden Hannah" not in body, name
    # Operator-only models are not visible to instructors.
    assert client.get(reverse("admin:learn_student_changelist")).status_code == 403
    assert client.get(reverse("admin:learn_toolcall_changelist")).status_code == 403


def test_question_form_options_one_per_line():
    from learn.admin import LinesListField

    field = LinesListField()
    assert field.clean("Paris\n Rome \n\nMadrid\n") == ["Paris", "Rome", "Madrid"]
    assert field.clean('["Paris", "Rome"]') == ["Paris", "Rome"]  # pasted JSON still works
    assert field.clean("") == []
    assert field.prepare_value(["a", "b"]) == "a\nb"
    assert not field.has_changed(["a", "b"], "a\nb\n")


def test_seed_english_creates_valid_class(instructor):
    from django.core.management import call_command

    from learn.models import Course, Question

    call_command("seed_english", "--username", instructor.user.username)
    call_command("seed_english", "--username", instructor.user.username)  # idempotent
    course = Course.objects.get(instructor=instructor)
    assert course.lessons.count() == 3 and course.quizzes.count() == 3
    assert Question.objects.filter(quiz__course=course).count() == 12
