import json


from learn.models import Answer, Enrollment
from learn.services import tokens


def post(client, url, data=None, method="post"):
    return getattr(client, method)(url, json.dumps(data or {}), content_type="application/json")


def test_student_join_connect_me_leave(client, course_setup):
    course = course_setup[0]
    info = client.get(f"/api/classes/{course.join_code.lower()}").json()
    assert info["title"] == course.title and not info["linked"]

    bad = post(client, f"/api/classes/{course.join_code}/join", {"name": "Sam", "email": "s@example.com"})
    assert bad.status_code == 400 and "consent" in bad.json()["errors"]

    ok = post(client, f"/api/classes/{course.join_code}/join",
              {"name": "Sam", "email": "s@example.com", "consent": True})
    eid = ok.json()["enrollment_id"]
    conn = client.get(f"/api/connect/{eid}").json()
    raw = conn["mcp_url"].split("/s/")[1].split("/mcp")[0]
    assert tokens.resolve(raw).id == eid
    assert client.get(f"/api/connect/{eid}").json()["mcp_url"] is None  # shown once

    assert post(client, f"/api/enrollments/{eid}/regenerate").json()["ok"]
    assert client.get(f"/api/connect/{eid}").json()["mcp_url"]

    me = client.get("/api/me").json()
    assert me["enrollments"][0]["course"] == course.title
    assert client.get(f"/api/classes/{course.join_code}").json()["already_joined"]

    assert post(client, f"/api/enrollments/{eid}/leave").json()["ok"]
    assert not Enrollment.objects.exists()


def test_other_session_cannot_see_enrollment(client, enrolled):
    enrollment, _ = enrolled
    assert client.get(f"/api/connect/{enrollment.id}").status_code == 404


def test_restore(client, enrolled):
    enrollment, raw = enrolled
    assert post(client, "/api/restore", {"url": f"https://x/s/{raw}/mcp"}).json()["ok"]
    assert client.get("/api/me").json()["enrollments"][0]["id"] == enrollment.id


def test_teach_requires_login(client, db):
    assert client.get("/api/teach/courses").status_code == 401


def test_signup_and_full_authoring_flow(client, db):
    r = post(client, "/api/auth/signup", {"username": "zoe", "email": "z@example.com", "display_name": "Zoe",
                                          "password1": "a-Strong-pass-42", "password2": "a-Strong-pass-42"})
    assert r.status_code == 200 and client.get("/api/auth/me").json()["user"]["username"] == "zoe"

    course = post(client, "/api/teach/courses", {"title": "English", "description": "d"}).json()
    lesson = post(client, f"/api/teach/courses/{course['id']}/lessons", {"title": "L1", "brief": "Teach greetings"}).json()
    assert lesson["order"] == 1
    assert post(client, f"/api/teach/courses/{course['id']}/lessons", {"title": "empty"}).status_code == 400

    quiz = post(client, f"/api/teach/courses/{course['id']}/quizzes",
                {"title": "Q", "lesson_id": lesson["id"], "mode": "manual"}).json()
    q = post(client, f"/api/teach/quizzes/{quiz['id']}/questions",
             {"type": "mcq", "prompt": "Hi?", "options": ["a", "b"], "correct_answer": "B"}).json()
    assert q["options"] == ["a", "b"]
    assert post(client, f"/api/teach/quizzes/{quiz['id']}/questions",
                {"type": "mcq", "prompt": "x", "options": ["only"], "correct_answer": "A"}).status_code == 400
    upd = post(client, f"/api/teach/quizzes/{quiz['id']}", {"mode": "ai", "prompt": "5 qs", "ai_question_count": 5},
               method="patch").json()
    assert upd["mode"] == "ai" and upd["question_count"] == 5

    detail = client.get(f"/api/teach/courses/{course['id']}").json()
    assert detail["lessons"][0]["title"] == "L1" and detail["quizzes"][0]["mode"] == "ai"
    assert client.get(f"/api/teach/courses/{course['id']}/dashboard").json()["student_count"] == 0
    assert post(client, f"/api/teach/questions/{q['id']}", method="delete").json()["ok"]


def test_teach_scoping_and_review(client, course_setup, enrolled, other_instructor):
    course, lesson1, _, quiz = course_setup
    enrollment, _ = enrolled
    from learn.models import QuizAttempt

    attempt = QuizAttempt.objects.create(enrollment=enrollment, quiz=quiz)
    question = quiz.questions.get(type="short")
    answer = Answer.objects.create(attempt=attempt, question=question, raw_answer="typ", status=Answer.NEEDS_REVIEW)

    client.force_login(other_instructor.user)
    assert client.get(f"/api/teach/courses/{course.id}").status_code == 404
    assert client.get("/api/teach/courses").json()["courses"] == []

    client.force_login(course.instructor.user)
    review = client.get(f"/api/teach/courses/{course.id}/review").json()["answers"]
    assert review[0]["id"] == answer.id
    r = post(client, f"/api/teach/answers/{answer.id}", {"status": "correct"}, method="patch")
    assert r.status_code == 200
    student = client.get(f"/api/teach/students/{enrollment.id}").json()
    assert student["attempts"][0]["answers"][0]["status"] == "correct"


def test_login_logout(client, instructor):
    assert post(client, "/api/auth/login", {"username": "alice", "password": "wrong"}).status_code == 400
    assert post(client, "/api/auth/login", {"username": "alice", "password": "pw-123456!"}).json()["user"]
    assert post(client, "/api/auth/logout").json()["ok"]
    assert client.get("/api/auth/me").json()["user"] is None


def test_csrf_failure_is_json(db):
    from django.test import Client

    c = Client(enforce_csrf_checks=True)
    r = c.post("/api/auth/logout", "{}", content_type="application/json")
    assert r.status_code == 403 and "session" in r.json()["error"].lower()


def test_instructor_tracks_and_resolves_student_problems(client, instructor, other_instructor, course_setup):
    from learn.models import Event
    from learn.services import enrollments, quizzes

    course, lesson1, _, quiz = course_setup
    enr, _ = enrollments.join(course, name="Sam", email="sam@example.com")
    start = quizzes.start(enr, quiz.id)
    r = quizzes.grade_and_next(enr, start["attempt_id"], start["question"]["question_id"], "A")
    quizzes.grade_and_next(enr, start["attempt_id"], r["next_question"]["question_id"], "type()")
    quizzes.submit_report(enr, start["attempt_id"], "Confused ints and floats.", ["number types"])
    enrollments.report_problem(enr, lesson_id=lesson1.id, concept="Floats", category="concept", note="decimals?")

    client.force_login(instructor.user)
    dash = client.get(f"/api/teach/courses/{course.id}/dashboard").json()
    assert dash["open_problem_count"] == 2
    assert dash["students"][0]["problem_count"] == 2
    assert {p["category"] for p in dash["problems"]} == {"quiz_mistakes", "concept"}
    assert any(w["concept"] == "number types" for w in dash["weak_concepts"])

    detail = client.get(f"/api/teach/students/{enr.id}").json()
    attempt = detail["attempts"][0]
    assert attempt["summary"] == "Confused ints and floats." and attempt["incorrect"] == 1
    assert len(detail["problems"]) == 2

    pid = Event.objects.get(enrollment=enr, category="concept").id
    resp = post(client, f"/api/teach/problems/{pid}", {"resolved": True, "instructor_note": "Explained in class"}, "patch")
    assert resp.status_code == 200 and resp.json()["resolved_at"]
    assert client.get(f"/api/teach/courses/{course.id}/dashboard").json()["open_problem_count"] == 1

    client.force_login(other_instructor.user)
    assert post(client, f"/api/teach/problems/{pid}", {"resolved": False}, "patch").status_code == 404
