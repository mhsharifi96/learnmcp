import json
import re

import pytest

from learn.models import Answer, Event, PackSubmission, Quiz, QuizAttempt
from learn.services import ServiceError, packs, tokens

BASE = "https://learn.example"


def _key(prompt: str) -> str:
    return re.search(r"https://learn\.example/r/([^\s\"<?]+)", prompt).group(1)


def test_manual_quiz_prompt_has_form_but_no_answers(enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    prompt = packs.quiz_prompt(enrollment, quiz.id, BASE)
    assert "Type of 3.5?" in prompt and 'type="radio"' in prompt
    assert "Decimals are floats" not in prompt  # explanation leaks the answer
    assert "type()" not in prompt  # accepted answer
    assert not QuizAttempt.objects.exists()  # nothing until the student submits


def test_manual_quiz_form_post_grades_once(client, enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    q_mcq = quiz.questions.get(order=1)
    q_short = quiz.questions.get(order=2)
    key = _key(packs.quiz_prompt(enrollment, quiz.id, BASE))

    r = client.post(f"/r/{key}", {f"a{q_mcq.id}": "B", f"a{q_short.id}": "len"}, HTTP_ORIGIN="https://gemini.google.com")
    assert r.status_code == 200
    attempt = QuizAttempt.objects.get()
    assert attempt.finished_at and attempt.score == 0.5
    assert dict(attempt.answers.values_list("question_id", "status")) == {
        q_mcq.id: Answer.CORRECT,
        q_short.id: Answer.NEEDS_REVIEW,
    }
    assert Event.objects.filter(type=Event.QUIZ_FINISHED, client="prompt:gemini").exists()
    assert "50%" in r.content.decode()

    # A second submission of the same prompt is ignored.
    r = client.post(f"/r/{key}", {f"a{q_mcq.id}": "A"})
    assert r.status_code == 200
    assert QuizAttempt.objects.count() == 1 and PackSubmission.objects.count() == 1


def test_manual_quiz_pasted_json_list(client, enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    key = _key(packs.quiz_prompt(enrollment, quiz.id, BASE))
    pasted = 'Here you go:\n```json\n{"answers": ["float", "type()"], "app": "DeepSeek"}\n```'
    r = client.post(f"/r/{key}", {"d": pasted})
    assert r.status_code == 200
    attempt = QuizAttempt.objects.get()
    assert attempt.score == 1.0
    assert Event.objects.filter(type=Event.QUIZ_FINISHED, client="prompt:deepseek").exists()


def test_ai_quiz_json(client, enrolled, course_setup):
    enrollment, _ = enrolled
    course = course_setup[0]
    quiz = Quiz.objects.create(course=course, title="AI quiz", mode=Quiz.AI, prompt="2 questions", ai_question_count=2)
    key = _key(packs.quiz_prompt(enrollment, quiz.id, BASE))
    data = {
        "items": [
            {"q": "2+2?", "options": ["3", "4"], "correct": "B", "answer": "B", "ok": True, "concept": "add"},
            {"q": "3*3?", "options": [], "correct": "9", "answer": "6", "ok": False, "concept": "multiply"},
            {"q": "extra beyond the count", "answer": "x", "ok": True},
        ],
        "summary": "Good at adding, weak at multiplying.",
        "weak_concepts": ["multiply"],
    }
    r = client.post(f"/r/{key}?format=json", {"d": json.dumps(data)})
    assert r.status_code == 200 and r["Access-Control-Allow-Origin"] == "*"
    body = r.json()["quizzes"][0]
    assert body["score_percent"] == 50 and body["total"] == 2
    attempt = QuizAttempt.objects.get()
    assert attempt.generated_questions.count() == 2
    assert attempt.summary.startswith("Good at adding")
    assert Event.objects.get(type=Event.PROBLEM).concept == "multiply"


def test_lesson_feedback_reports_problem(client, enrolled, course_setup):
    enrollment, _ = enrolled
    lesson = course_setup[1]
    prompt = packs.lesson_prompt(enrollment, lesson.id, BASE)
    assert "x = 1" in prompt
    assert Event.objects.filter(type=Event.LESSON_STARTED, client="prompt").exists()
    key = _key(prompt)
    d = json.dumps({"understood": 2, "difficult": ["variables"], "summary": "Confused names and values."})
    r = client.get(f"/r/{key}", {"d": d})
    assert r.status_code == 200
    assert Event.objects.filter(type=Event.LESSON_FEEDBACK).exists()
    problem = Event.objects.get(type=Event.PROBLEM)
    assert problem.severity == Event.HIGH and problem.concept == "variables"


def test_key_dies_with_new_link_and_tampering(client, enrolled, course_setup):
    enrollment, _ = enrolled
    quiz = course_setup[3]
    key = _key(packs.quiz_prompt(enrollment, quiz.id, BASE))
    with pytest.raises(ServiceError):
        packs.read_key(key[:-2] + "xx")
    tokens.assign_new_token(enrollment)
    with pytest.raises(ServiceError):
        packs.read_key(key)
    r = client.post(f"/r/{key}", {"d": '{"answers": ["B"]}'})
    assert r.status_code == 400


def test_get_without_data_shows_paste_form(client, enrolled, course_setup):
    enrollment, _ = enrolled
    key = _key(packs.quiz_prompt(enrollment, course_setup[3].id, BASE))
    r = client.get(f"/r/{key}")
    assert r.status_code == 200 and 'name="d"' in r.content.decode()


def test_study_api(client, course_setup):
    from tests.test_api import post, signup_student, verify_from_outbox

    course = course_setup[0]
    signup_student(client)
    verify_from_outbox(client)
    enr_id = post(client, f"/api/classes/{course.join_code}/join", {"consent": True}).json()["enrollment_id"]
    data = client.get(f"/api/enrollments/{enr_id}/study").json()
    assert [l["title"] for l in data["course"]["lessons"]] == ["Variables", "Loops"]
    r = post(client, f"/api/enrollments/{enr_id}/prompt", {"quiz_id": course_setup[3].id})
    assert r.status_code == 200 and "/r/" in r.json()["prompt"]


def test_lesson_and_quizzes_in_one_send(client, enrolled, course_setup):
    """One prompt per lesson: lesson feedback, the AI quiz and the instructor's quiz arrive in one POST."""
    enrollment, _ = enrolled
    lesson, manual = course_setup[1], course_setup[3]
    ai = Quiz.objects.create(
        course=lesson.course, lesson=lesson, title="AI check", mode=Quiz.AI, prompt="1 question", ai_question_count=1
    )
    prompt = packs.lesson_prompt(enrollment, lesson.id, BASE)
    assert "Type of 3.5?" in prompt and 'type="radio"' in prompt  # instructor quiz inside the final page
    assert f"quiz_id {ai.id}" in prompt and "Decimals are floats" not in prompt
    assert prompt.count("RESULT_JSON") >= 1
    key = _key(prompt)
    q_mcq = manual.questions.get(order=1)
    d = {
        "understood": 4,
        "summary": "Fine.",
        "quizzes": {str(ai.id): {"items": [{"q": "x?", "answer": "y", "correct": "z", "ok": False}]}},
        "app": "chatgpt",
    }
    r = client.post(f"/r/{key}", {"d": json.dumps(d), f"a{q_mcq.id}": "B"})
    assert r.status_code == 200, r.content.decode()[:500]
    sub = PackSubmission.objects.get()
    assert sub.kind == "unit" and len(sub.attempt_ids) == 2 and sub.event is not None
    scores = dict(QuizAttempt.objects.values_list("quiz_id", "score"))
    assert scores == {ai.id: 0.0, manual.id: 0.5}
    html = r.content.decode()
    assert "AI check" in html and "Variables quiz" in html


def test_lesson_send_with_only_manual_answers_in_json(client, enrolled, course_setup):
    enrollment, _ = enrolled
    lesson, manual = course_setup[1], course_setup[3]
    key = _key(packs.lesson_prompt(enrollment, lesson.id, BASE))
    r = client.get(f"/r/{key}", {"d": json.dumps({"manual": {str(manual.id): ["B", "type"]}})})
    assert r.status_code == 200
    assert QuizAttempt.objects.get().score == 1.0
    assert not Event.objects.filter(type=Event.LESSON_FEEDBACK).exists()


def test_lesson_send_empty_is_rejected(client, enrolled, course_setup):
    enrollment, _ = enrolled
    key = _key(packs.lesson_prompt(enrollment, course_setup[1].id, BASE))
    r = client.post(f"/r/{key}", {"d": "{}"})
    assert r.status_code == 400 and not PackSubmission.objects.exists()
