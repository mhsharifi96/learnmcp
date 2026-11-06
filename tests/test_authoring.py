import json

import pytest

from learn.models import Lesson, Question, Quiz
from learn.services import ServiceError, authoring, courses, packs, quizzes

IMPORT = {
    "lessons": [
        {
            "title": "Functions",
            "kind": "general",
            "objectives": ["define a function", "return a value"],
            "brief": "Teach def, parameters and return with small examples.",
            "content": "",
            "teaching_notes": "Watch for print vs return.",
            "quizzes": [
                {
                    "title": "Functions quiz",
                    "mode": "manual",
                    "questions": [
                        {"type": "mcq", "prompt": "Keyword to define a function?", "options": ["func", "def", "fn"],
                         "correct_answer": "B", "explanation": "def", "concept": "def"},
                        {"type": "short", "prompt": "Keyword to give a value back?", "correct_answer": "return",
                         "accepted_answers": ["return x"]},
                    ],
                },
                {"title": "Practice", "mode": "ai", "prompt": "Ask about scope", "question_count": 4},
            ],
        }
    ],
    "quizzes": [{"title": "Class review", "mode": "ai", "prompt": "Mixed review", "question_count": 6, "lesson_id": None}],
}


def test_prompt_describes_class_and_shape(course_setup):
    course = course_setup[0]
    prompt = authoring.build_prompt(course, "Teach functions to beginners", "lessons")
    assert "Python 101" in prompt and "Teach functions to beginners" in prompt
    assert '"lessons"' in prompt and "grammar" in prompt and "Variables" in prompt
    quiz_prompt = authoring.build_prompt(course, "quiz on loops", "quizzes")
    assert f"lesson_id {course_setup[2].id}" in quiz_prompt
    with pytest.raises(ServiceError):
        authoring.build_prompt(course, "  ")


def test_import_creates_drafts_hidden_from_students(course_setup, enrolled):
    course = course_setup[0]
    enrollment, _ = enrolled
    reply = "Here it is:\n```json\n" + json.dumps(IMPORT, ensure_ascii=False) + "\n```\nCopy it."
    assert authoring.import_json(course, reply) == {"lessons": 1, "quizzes": 3}

    lesson = Lesson.objects.get(title="Functions")
    assert lesson.draft and lesson.order == 3 and lesson.objectives_list == ["define a function", "return a value"]
    manual = Quiz.objects.get(title="Functions quiz")
    assert manual.draft and manual.lesson == lesson and manual.questions.count() == 2
    assert manual.questions.get(order=2).type == Question.SHORT
    assert Quiz.objects.get(title="Class review").lesson is None

    titles = [l["title"] for l in courses.list_courses(enrollment)["courses"][0]["lessons"]]
    assert "Functions" not in titles
    with pytest.raises(ServiceError):
        courses.get_lesson(enrollment, lesson.id)
    with pytest.raises(ServiceError):
        quizzes.start(enrollment, manual.id)
    with pytest.raises(ServiceError):
        packs.lesson_prompt(enrollment, lesson.id, "https://x")

    # Publishing the lesson alone keeps its draft quizzes hidden.
    lesson.draft = False
    lesson.save()
    data = courses.list_courses(enrollment)["courses"][0]
    published = next(l for l in data["lessons"] if l["title"] == "Functions")
    assert published["quizzes"] == []

    assert authoring.publish_all(course) == {"lessons": 0, "quizzes": 3}
    data = courses.list_courses(enrollment)["courses"][0]
    published = next(l for l in data["lessons"] if l["title"] == "Functions")
    assert {q["title"] for q in published["quizzes"]} == {"Functions quiz", "Practice"}
    assert quizzes.start(enrollment, manual.id)


def test_import_is_all_or_nothing(course_setup):
    course = course_setup[0]
    bad = json.loads(json.dumps(IMPORT))
    bad["lessons"][0]["quizzes"][0]["questions"][0]["correct_answer"] = "Z"
    bad["quizzes"][0]["lesson_id"] = 99999
    with pytest.raises(ServiceError) as exc:
        authoring.import_json(course, json.dumps(bad))
    assert "question 1" in str(exc.value) and "lesson_id 99999" in str(exc.value)
    assert not Lesson.objects.filter(title="Functions").exists() and not Quiz.objects.filter(draft=True).exists()
    with pytest.raises(ServiceError):
        authoring.import_json(course, "{not json")
    with pytest.raises(ServiceError):
        authoring.import_json(course, "{}")


def test_import_quizzes_into_existing_lesson(course_setup):
    course, lesson1, lesson2, _ = course_setup
    data = {"quizzes": [{"title": "Loops quiz", "mode": "ai", "prompt": "for/while", "lesson_id": lesson2.id}]}
    authoring.import_json(course, json.dumps(data))
    quiz = Quiz.objects.get(title="Loops quiz")
    assert quiz.lesson == lesson2 and quiz.draft


def test_api_flow_and_scoping(client, course_setup, other_instructor):
    course = course_setup[0]
    client.force_login(other_instructor.user)
    r = client.post(f"/api/teach/courses/{course.id}/import", {"json": json.dumps(IMPORT)}, content_type="application/json")
    assert r.status_code == 404

    client.force_login(course.instructor.user)
    r = client.post(f"/api/teach/courses/{course.id}/ai-prompt", {"goal": "functions"}, content_type="application/json")
    assert r.status_code == 200 and "functions" in r.json()["prompt"]
    r = client.post(f"/api/teach/courses/{course.id}/import", {"json": json.dumps(IMPORT)}, content_type="application/json")
    assert r.status_code == 200 and r.json()["lessons"] == 1
    detail = client.get(f"/api/teach/courses/{course.id}").json()
    assert [l["draft"] for l in detail["lessons"]] == [False, False, True]
    lesson_id = detail["lessons"][-1]["id"]
    r = client.patch(f"/api/teach/lessons/{lesson_id}", {"draft": False}, content_type="application/json")
    assert r.status_code == 200 and r.json()["draft"] is False
    r = client.post(f"/api/teach/courses/{course.id}/publish", {}, content_type="application/json")
    assert r.json() == {"lessons": 0, "quizzes": 3}
