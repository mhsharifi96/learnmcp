from django.contrib.auth import get_user_model
from django.urls import reverse

from learn.models import Enrollment, Event, Instructor, Student
from learn.services import tokens


def test_signup_creates_staff_instructor(client, db):
    resp = client.post(
        reverse("learn:signup"),
        {"username": "carol", "email": "c@example.com", "display_name": "Carol",
         "password1": "a-Strong-pass-42", "password2": "a-Strong-pass-42"},
    )
    assert resp.status_code == 302
    user = get_user_model().objects.get(username="carol")
    assert user.is_staff and not user.is_superuser
    assert user.groups.filter(name="Instructors").exists()
    assert user.has_perm("learn.add_course") and not user.has_perm("learn.delete_enrollment")
    assert Instructor.objects.get(user=user).display_name == "Carol"


def test_join_flow_requires_consent_and_age(client, course_setup):
    course = course_setup[0]
    url = reverse("learn:join", args=[course.join_code])
    page = client.get(url).content.decode()
    assert "Not recorded" in page and "conversation" in page
    resp = client.post(url, {"name": "Sam", "email": "sam@example.com", "consent": "on"})
    assert resp.status_code == 200 and not Enrollment.objects.exists()  # age box missing

    resp = client.post(url, {"name": "Sam", "email": "sam@example.com", "consent": "on", "is_adult": "on"})
    enrollment = Enrollment.objects.get()
    assert resp.url == reverse("learn:connect", args=[enrollment.pk])

    page = client.get(resp.url).content.decode()
    raw = page.split("/s/")[1].split("/mcp")[0]
    assert tokens.resolve(raw) == enrollment
    # Shown only once.
    assert "/s/" not in client.get(resp.url).content.decode().split("Regenerate")[0]


def test_join_code_lookup(client, course_setup):
    course = course_setup[0]
    resp = client.get(reverse("learn:join_code"), {"code": course.join_code.lower()})
    assert resp.status_code == 302
    resp = client.get(reverse("learn:join_code"), {"code": "NOPE"})
    assert "No class with this code" in resp.content.decode()


def test_second_class_links_same_student(client, course_setup, other_instructor):
    from tests.conftest import make_course

    first = course_setup[0]
    second = make_course(other_instructor, "Other")[0]
    data = {"name": "Sam", "email": "sam@example.com", "consent": "on", "is_adult": "on"}
    client.post(reverse("learn:join", args=[first.join_code]), data)
    resp = client.post(reverse("learn:join", args=[second.join_code]), data)
    assert Student.objects.count() == 1 and Enrollment.objects.count() == 2
    assert "already includes this class" in client.get(resp.url).content.decode()


def test_my_data_regenerate_and_leave(client, course_setup):
    course, lesson1, *_ = course_setup
    client.post(
        reverse("learn:join", args=[course.join_code]),
        {"name": "Sam", "email": "sam@example.com", "consent": "on", "is_adult": "on"},
    )
    enrollment = Enrollment.objects.get()
    Event.objects.create(enrollment=enrollment, type=Event.STUCK, lesson=lesson1, concept="floats")
    page = client.get(reverse("learn:me")).content.decode()
    assert "floats" in page and course.title in page

    old_hash = enrollment.token_hash
    client.post(reverse("learn:regenerate", args=[enrollment.pk]))
    enrollment.refresh_from_db()
    assert enrollment.token_hash != old_hash

    client.post(reverse("learn:leave", args=[enrollment.pk]))
    assert not Enrollment.objects.exists() and not Event.objects.exists() and not Student.objects.exists()


def test_other_browser_cannot_manage_enrollment(client, enrolled):
    enrollment, raw = enrolled
    assert client.post(reverse("learn:leave", args=[enrollment.pk])).status_code == 404
    assert Enrollment.objects.filter(pk=enrollment.pk).exists()
    # Restore with the personal URL grants access.
    client.post(reverse("learn:restore"), {"url": f"https://host/s/{raw}/mcp"})
    assert enrollment.course.title in client.get(reverse("learn:me")).content.decode()


def test_healthz(client, db):
    assert client.get("/healthz").json() == {"status": "ok", "db": True}
