import pytest
from django.core.management import call_command

from learn.management.commands.seed_samples import CLASSES
from learn.models import Course, Lesson, Question, Quiz


@pytest.mark.django_db
def test_seed_samples_is_idempotent():
    call_command("seed_samples")
    courses = Course.objects.filter(instructor__user__username="demo")
    assert courses.count() == len(CLASSES)
    counts = (Lesson.objects.count(), Quiz.objects.count(), Question.objects.count())
    for course in courses:
        assert 3 <= course.lessons.count() <= 5
        assert course.quizzes.filter(mode=Quiz.MANUAL).exists() and course.quizzes.filter(mode=Quiz.AI).exists()
        assert course.listed
    call_command("seed_samples")
    assert courses.count() == len(CLASSES)
    assert (Lesson.objects.count(), Quiz.objects.count(), Question.objects.count()) == counts


@pytest.mark.django_db
def test_seed_samples_dry_run_creates_nothing():
    call_command("seed_samples", "--dry-run")
    assert Course.objects.count() == 0


def test_class_info_lists_lesson_titles_only_for_listed(client, instructor):
    course = Course.objects.create(instructor=instructor, title="Algebra")
    Lesson.objects.create(course=course, order=2, title="Second", brief="b")
    Lesson.objects.create(course=course, order=1, title="First", brief="a", content="secret text")
    data = client.get(f"/api/classes/{course.join_code}").json()
    assert data["listed"] is True
    assert data["lessons"] == [{"order": 1, "title": "First"}, {"order": 2, "title": "Second"}]

    course.listed = False
    course.save()
    data = client.get(f"/api/classes/{course.join_code}").json()
    assert data["listed"] is False and data["lessons"] == []
