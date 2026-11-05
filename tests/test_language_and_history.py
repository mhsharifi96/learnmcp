import json

from learn.models import Event, Lesson
from learn.services import courses, history, packs, quizzes
from tests.test_api import post, signup_student, verify_from_outbox


def test_lesson_kind_rules_reach_mcp_and_prompt(enrolled, course_setup):
    enrollment, _ = enrolled
    lesson = course_setup[1]
    lesson.kind = "translation"
    lesson.save()
    data = courses.get_lesson(enrollment, lesson.id)
    assert data["lesson_type"] == "translation" and "TRANSLATION LESSON" in data["how_to_teach"]
    assert "TRANSLATION LESSON" in packs.lesson_prompt(enrollment, lesson.id, "https://x.example")


def test_instructor_sets_lesson_kind(client, instructor, course_setup):
    client.force_login(instructor.user)
    course = course_setup[0]
    r = post(client, f"/api/teach/courses/{course.id}/lessons", {"title": "Speak", "kind": "speaking", "brief": "Talk"})
    assert r.status_code == 201 and r.json()["kind"] == "speaking"
    r = post(client, f"/api/teach/lessons/{r.json()['id']}", {"kind": "nope"}, method="patch")
    assert r.status_code == 400


def test_catalog_lists_only_listed(client, instructor, other_instructor, course_setup):
    from tests.conftest import make_course

    hidden, *_ = make_course(other_instructor, title="Hidden")
    hidden.listed = False
    hidden.save()
    data = client.get("/api/classes").json()["classes"]
    assert [c["title"] for c in data] == ["Python 101"]
    assert data[0]["instructor"] == "Alice" and data[0]["lessons"] == 2 and not data[0]["joined"]

    signup_student(client)
    verify_from_outbox(client)
    post(client, f"/api/classes/{course_setup[0].join_code}/join", {"consent": True})
    assert client.get("/api/classes").json()["classes"][0]["joined"] is True


def test_timeline_is_readable(enrolled, course_setup):
    enrollment, _ = enrolled
    _, lesson1, _, quiz = course_setup
    courses.get_lesson(enrollment, lesson1.id, client="claude")
    courses.get_lesson(enrollment, lesson1.id, client="claude")  # same day: one entry
    start = quizzes.start(enrollment, quiz.id)
    r = quizzes.grade_and_next(enrollment, start["attempt_id"], start["question"]["question_id"], "B")
    quizzes.grade_and_next(enrollment, start["attempt_id"], r["next_question"]["question_id"], "len")
    items = history.timeline(enrollment)
    kinds = [i["type"] for i in items]
    assert kinds.count("lesson") == 1 and kinds.count("quiz") == 1
    quiz_item = next(i for i in items if i["type"] == "quiz")
    assert quiz_item["score_percent"] == 50 and quiz_item["total"] == 2 and quiz_item["finished"]
    assert items[-1]["app"] == {"name": "Claude", "via": "mcp"}
    prog = history.progress(enrollment)
    assert prog["lessons_total"] == 2 and prog["lessons_done"] == 1 and prog["next_lesson"]["title"] == "Loops"


def test_timeline_lesson_feedback_from_prompt(client, enrolled, course_setup):
    enrollment, _ = enrolled
    lesson = course_setup[1]
    prompt = packs.lesson_prompt(enrollment, lesson.id, "https://learn.example")
    import re

    key = re.search(r"https://learn\.example/r/([^\s\"<?]+)", prompt).group(1)
    client.get(f"/r/{key}", {"d": json.dumps({"understood": 3, "difficult": ["be"], "summary": "Ok.", "app": "gemini"})})
    fb = next(i for i in history.timeline(enrollment) if i["type"] == "feedback")
    assert fb["understood"] == 3 and fb["difficult"] == ["be"] and fb["note"] == "Ok."
    assert fb["app"] == {"name": "Gemini", "via": "prompt"}
    assert Event.objects.filter(type=Event.LESSON_FEEDBACK).count() == 1


def test_add_language_lessons_command(instructor):
    from django.core.management import call_command

    from learn.models import Course

    course = Course.objects.create(instructor=instructor, title="English")
    call_command("build_english_course", join_code=course.join_code)
    before = course.lessons.count()
    call_command("add_language_lessons", join_code=course.join_code)
    lessons = list(course.lessons.order_by("order"))
    assert len(lessons) == before + 24
    assert [l.order for l in lessons] == list(range(1, len(lessons) + 1))
    titles = [l.title for l in lessons]
    # A1 skills come right after the A1 lessons, before A2 starts.
    a1_writing = titles.index("A1 · Writing")
    assert titles[a1_writing + 1].startswith("A2")
    kinds = {l.title: l.kind for l in lessons}
    assert kinds["A1 · 20 key words"] == "vocabulary" and kinds["A1 · Persian → English + grammar"] == "translation"
    assert kinds["Placement test — start here"] == "general"
    assert sum(1 for k in kinds.values() if k == "grammar") == 6
    call_command("add_language_lessons", join_code=course.join_code)  # idempotent
    assert course.lessons.count() == before + 24


def test_study_shows_what_was_sent(client, course_setup):
    import re

    course, lesson1, _, quiz = course_setup
    signup_student(client)
    verify_from_outbox(client)
    enr_id = post(client, f"/api/classes/{course.join_code}/join", {"consent": True}).json()["enrollment_id"]
    data = client.get(f"/api/enrollments/{enr_id}/study").json()["course"]
    assert data["lessons"][0]["sent"] is None and data["lessons"][0]["quizzes"][0]["last"] is None

    prompt = post(client, f"/api/enrollments/{enr_id}/prompt", {"lesson_id": lesson1.id}).json()["prompt"]
    key = re.search(r"/r/([^\s\"<?]+)", prompt).group(1)
    q1 = quiz.questions.get(order=1)
    client.post(f"/r/{key}", {"d": json.dumps({"understood": 4, "summary": "ok"}), f"a{q1.id}": "B"})
    data = client.get(f"/api/enrollments/{enr_id}/study").json()["course"]
    first = data["lessons"][0]
    assert first["sent"]["understood"] == 4
    assert first["quizzes"][0]["last"]["score_percent"] == 50
