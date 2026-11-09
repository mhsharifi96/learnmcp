"""Classes that need the site admin's approval: pending students get no lessons, quizzes or MCP access."""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail

from learn.models import Course, Enrollment
from learn.services import ServiceError, courses, enrollments, quizzes, tokens

from .test_api import post, signup_student, verify_from_outbox


@pytest.fixture
def gated(course_setup):
    course = course_setup[0]
    Course.objects.filter(pk=course.pk).update(requires_approval=True)
    course.refresh_from_db()
    return course_setup


def test_pending_registration_flow(client, gated):
    course = gated[0]
    info = client.get(f"/api/classes/{course.join_code}").json()
    assert info["requires_approval"] is True and info["quizzes"] == 1

    signup_student(client)
    verify_from_outbox(client)
    ok = post(client, f"/api/classes/{course.join_code}/join", {"consent": True}).json()
    assert ok["pending"] is True
    eid = ok["enrollment_id"]

    conn = client.get(f"/api/connect/{eid}").json()
    assert conn["pending"] is True and conn["mcp_url"] is None
    assert client.get(f"/api/enrollments/{eid}/study").status_code == 403
    assert post(client, f"/api/enrollments/{eid}/regenerate").status_code == 403
    assert client.get(f"/api/classes/{course.join_code}").json()["pending"] is True
    assert client.get("/api/me").json()["enrollments"][0]["approved"] is False

    # The site admin approves: the student is emailed and can make a link.
    mail.outbox.clear()
    assert enrollments.approve(Enrollment.objects.filter(pk=eid), base_url="https://x") == 1
    assert len(mail.outbox) == 1 and "https://x/me/" in mail.outbox[0].body
    assert client.get(f"/api/enrollments/{eid}/study").status_code == 200
    assert post(client, f"/api/enrollments/{eid}/regenerate").json()["ok"]
    raw = client.get(f"/api/connect/{eid}").json()["mcp_url"].split("/s/")[1].split("/mcp")[0]
    assert tokens.resolve(raw).id == eid


def test_pending_token_and_lessons_are_blocked(gated):
    course, lesson1, _, quiz = gated
    enr, raw = enrollments.join(course, name="P", email="p@example.com")
    assert not enr.approved
    assert tokens.resolve(raw) is None
    with pytest.raises(ServiceError):
        courses.get_accessible_lesson(enr, lesson1.id)
    with pytest.raises(ServiceError):
        quizzes.start(enr, quiz.id)

    enrollments.approve(Enrollment.objects.filter(pk=enr.pk))
    enr.refresh_from_db()
    assert tokens.resolve(raw).id == enr.id
    assert courses.get_accessible_lesson(enr, lesson1.id) == lesson1


def test_open_classes_approve_on_join(enrolled):
    enrollment, raw = enrolled
    assert enrollment.approved and tokens.resolve(raw) is not None


def test_admin_approve_action(client, gated):
    course = gated[0]
    enr, _ = enrollments.join(course, name="P", email="p@example.com")
    admin = get_user_model().objects.create_superuser("root", "r@example.com", "pw-123456!")
    client.force_login(admin)
    r = client.post(
        "/admin/learn/enrollment/", {"action": "approve_selected", "_selected_action": [enr.pk]}, follow=True
    )
    assert r.status_code == 200
    enr.refresh_from_db()
    assert enr.approved


@pytest.mark.django_db
def test_seed_free_courses():
    from django.core.management import call_command

    from learn.management.free_courses import COURSES
    from learn.models import Lesson, Quiz

    call_command("seed_free_courses")
    qs = Course.objects.filter(instructor__user__username="academy")
    assert qs.count() == len(COURSES) == 200
    assert all("رایگان" in c.title and c.requires_approval and c.listed for c in qs)
    assert not Quiz.objects.filter(course__in=qs).exists()
    assert not Lesson.objects.filter(course__in=qs).exclude(content="", brief="").exists()
    n = Lesson.objects.count()
    call_command("seed_free_courses")
    assert qs.count() == 200 and Lesson.objects.count() == n
