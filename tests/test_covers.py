from django.core.files.uploadedfile import SimpleUploadedFile

from learn.models import Course
from learn.services import covers

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_theme_from_subject(instructor):
    assert covers.theme(Course(title="مبانی برنامه‌نویسی پایتون")) == "code"
    assert covers.theme(Course(title="IELTS Speaking")) == "language"
    assert covers.theme(Course(title="ریاضی دبیرستان: جبر")) == "math"
    assert covers.theme(Course(title="Cooking")) == "general"


def test_upload_serve_and_remove(client, course_setup, other_instructor):
    course = course_setup[0]
    url = f"/api/teach/courses/{course.id}/image"
    info = client.get(f"/api/classes/{course.join_code}").json()
    assert info["image"] is None and info["theme"] == "code"  # "Python 101"

    client.force_login(other_instructor.user)
    assert client.post(url, {"image": SimpleUploadedFile("a.png", PNG)}).status_code == 404

    client.force_login(course.instructor.user)
    bad = client.post(url, {"image": SimpleUploadedFile("a.txt", b"hello")})
    assert bad.status_code == 400
    r = client.post(url, {"image": SimpleUploadedFile("a.png", PNG, content_type="image/png")})
    assert r.status_code == 200 and r.json()["image"].startswith(f"/api/classes/{course.join_code}/image?v=")

    img = client.get(f"/api/classes/{course.join_code}/image")
    assert img.status_code == 200 and img["Content-Type"] == "image/png" and img.content == PNG
    listed = next(c for c in client.get("/api/classes").json()["classes"] if c["id"] == course.id)
    assert listed["image"] and listed["theme"] == "code"

    assert client.delete(url).json()["image"] is None
    assert client.get(f"/api/classes/{course.join_code}/image").status_code == 404
