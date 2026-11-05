import pytest
from django.contrib.auth import get_user_model

from learn.apps import ensure_instructors_group
from learn.models import Course, Instructor, Lesson, Question, Quiz
from learn.services import enrollments


def make_instructor(username="alice"):
    user = get_user_model().objects.create_user(username=username, password="pw-123456!", is_staff=True)
    user.groups.add(ensure_instructors_group())
    return Instructor.objects.create(user=user, display_name=username.title())


def make_course(instructor, title="Python 101"):
    course = Course.objects.create(instructor=instructor, title=title)
    lesson1 = Lesson.objects.create(course=course, order=1, title="Variables", content="x = 1")
    lesson2 = Lesson.objects.create(course=course, order=2, title="Loops", content="for ...")
    quiz = Quiz.objects.create(course=course, lesson=lesson1, title="Variables quiz")
    Question.objects.create(
        quiz=quiz, order=2, type="short", prompt="Function that shows a value's type?",
        correct_answer="type", accepted_answers_json=["type()"], explanation="type(x)", concept="type()",
    )
    Question.objects.create(
        quiz=quiz, order=1, type="mcq", prompt="Type of 3.5?", options_json=["int", "float", "str"],
        correct_answer="B", explanation="Decimals are floats.", concept="data types",
    )
    return course, lesson1, lesson2, quiz


@pytest.fixture
def instructor(db):
    return make_instructor("alice")


@pytest.fixture
def other_instructor(db):
    return make_instructor("bob")


@pytest.fixture
def course_setup(instructor):
    return make_course(instructor)


@pytest.fixture
def enrolled(course_setup):
    course = course_setup[0]
    enrollment, raw = enrollments.join(course, name="Sam", email="sam@example.com")
    return enrollment, raw
