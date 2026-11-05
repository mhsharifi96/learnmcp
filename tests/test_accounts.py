from datetime import timedelta

from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from learn.models import Enrollment, Student
from learn.services import accounts, enrollments, reminders
from tests.test_api import post, signup_student, verify_from_outbox


def test_signup_sends_verification_and_verify(client, db):
    data = signup_student(client)
    assert data["student"]["email_verified"] is False and data["email_sent"]
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["s@example.com"]
    who = client.get("/api/auth/me").json()
    assert who["student"]["email"] == "s@example.com" and who["user"] is None
    assert verify_from_outbox(client)["student"]["email_verified"]
    assert Student.objects.get().email_verified


def test_signup_validation(client, db):
    r = post(client, "/api/auth/student/signup", {"name": "", "email": "bad", "password1": "a", "password2": "b"})
    assert r.status_code == 400 and {"name", "email", "password2"} <= set(r.json()["errors"])
    signup_student(client)
    client.logout()
    r = post(client, "/api/auth/student/signup",
             {"name": "X", "email": "S@example.com", "password1": "Str0ng-pass!", "password2": "Str0ng-pass!"})
    assert "email" in r.json()["errors"]


def test_bad_and_tampered_tokens(client, db):
    assert post(client, "/api/auth/verify-email", {"token": "nope"}).status_code == 400
    signup_student(client)
    student = Student.objects.get()
    token = accounts.verification_token(student)
    student.email = "other@example.com"
    student.save()
    assert post(client, "/api/auth/verify-email", {"token": token}).status_code == 400


def test_login_and_resend_cooldown(client, db):
    signup_student(client)
    assert post(client, "/api/auth/verify-email/resend").status_code == 429
    client.logout()
    assert post(client, "/api/auth/student/login", {"email": "s@example.com", "password": "x"}).status_code == 400
    r = post(client, "/api/auth/student/login", {"email": " S@Example.com ", "password": "Str0ng-pass!"})
    assert r.status_code == 200 and r.json()["student"]["name"] == "Sam"


def test_signup_claims_anonymous_student(client, course_setup):
    course = course_setup[0]
    from learn import views as pages

    enr, _ = enrollments.join(course, name="Old", email="old@example.com")
    session = client.session
    session[pages.SESSION_STUDENT] = enr.student_id
    session[pages.SESSION_ENROLLMENTS] = [enr.id]
    session.save()
    signup_student(client, email="new@example.com")
    student = Student.objects.get()
    assert student.id == enr.student_id and student.user and student.email == "new@example.com"
    assert client.get("/api/me").json()["enrollments"][0]["id"] == enr.id


def test_settings_toggle_reminders(client, db):
    signup_student(client)
    r = post(client, "/api/me/settings", {"email_reminders": False}, method="patch")
    assert r.json()["student"]["email_reminders"] is False


def test_course_reminder_setting(client, instructor, course_setup):
    course = course_setup[0]
    client.force_login(instructor.user)
    url = f"/api/teach/courses/{course.id}"
    assert post(client, url, {"reminder_after_days": 400}, method="patch").status_code == 400
    assert post(client, url, {"reminder_after_days": 3}, method="patch").json()["reminder_after_days"] == 3


def _verified_enrollment(course, email="v@example.com"):
    student = Student.objects.create(name="Vee", email=email, email_verified_at=timezone.now(), lang="fa")
    enr, _ = enrollments.join(course, name="Vee", email=email, existing_student=student)
    return enr


def test_reminders(course_setup):
    course = course_setup[0]
    course.reminder_after_days = 3
    course.save()
    enr = _verified_enrollment(course)
    unverified, _ = enrollments.join(course, name="U", email="u@example.com")
    now = timezone.now()
    Enrollment.objects.filter(pk__in=[enr.pk, unverified.pk]).update(joined_at=now - timedelta(days=10))

    Enrollment.objects.filter(pk=enr.pk).update(last_activity_at=now - timedelta(days=1))
    assert reminders.send_due(now) == 0  # active recently

    Enrollment.objects.filter(pk=enr.pk).update(last_activity_at=now - timedelta(days=4))
    assert reminders.send_due(now) == 1
    assert mail.outbox[-1].to == ["v@example.com"] and "4" in mail.outbox[-1].subject
    assert reminders.send_due(now + timedelta(days=1)) == 0  # not again within N days
    assert reminders.send_due(now + timedelta(days=3, minutes=1)) == 1  # repeats every N days

    Student.objects.filter(pk=enr.student_id).update(email_reminders=False)
    assert reminders.send_due(now + timedelta(days=30)) == 0

    course.reminder_after_days = 0
    course.save()
    Student.objects.filter(pk=enr.student_id).update(email_reminders=True)
    assert reminders.send_due(now + timedelta(days=60)) == 0
    call_command("send_reminders", "--dry-run")
