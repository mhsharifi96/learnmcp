"""Create a demo instructor, class, lessons, quizzes and a demo student.

    python manage.py seed_demo [--base-url https://xyz.trycloudflare.com]
"""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from learn.apps import ensure_instructors_group
from learn.models import Course, Enrollment, Instructor, Lesson, Question, Quiz, Student
from learn.services import enrollments, tokens

DEMO_CODE = "DEMOPY"

LESSONS = [
    {
        "title": "Variables and types",
        "objectives": "Create variables\nRecognise int, float, str and bool\nUse type() to inspect a value",
        "content": (
            "A variable is a name that refers to a value: `age = 21`. Python works out the type from the value.\n\n"
            "Common types: int (21), float (3.5), str ('hello') and bool (True/False).\n"
            "Use type(x) to see the type of x. Strings can be joined with +, numbers added with +, "
            "but '2' + 2 is an error because the types differ. Convert with int('2') or str(2)."
        ),
        "teaching_notes": "Use small examples the student can type. Common mistake: mixing str and int with +.",
    },
    {
        "title": "Lists and loops",
        "objectives": "Create and index lists\nLoop over a list with for\nUse len() and append()",
        "content": (
            "A list holds several values in order: `fruits = ['apple', 'pear']`. Indexing starts at 0: fruits[0] "
            "is 'apple'. len(fruits) gives the number of items. fruits.append('kiwi') adds an item.\n\n"
            "A for loop repeats code for each item: `for f in fruits: print(f)`."
        ),
        "teaching_notes": "Off-by-one errors are the classic mistake here; ask what fruits[2] is for a 2-item list.",
    },
    {
        "title": "Functions",
        "objectives": "Define a function with def\nUse parameters and return values",
        "content": (
            "A function groups code under a name: `def greet(name): return 'Hi ' + name`. Call it with "
            "greet('Sam'). return sends a value back; print only shows it on screen."
        ),
        "teaching_notes": "Students often confuse print and return. Contrast them explicitly.",
    },
]

QUIZZES = {
    0: [
        {"type": "mcq", "prompt": "What is the type of the value 3.5?", "options": ["int", "float", "str", "bool"], "correct": "B",
         "explanation": "Numbers with a decimal point are floats.", "concept": "data types"},
        {"type": "mcq", "prompt": "What happens when you run '2' + 2?", "options": ["It prints 4", "It prints 22", "It raises a TypeError", "It prints '2 2'"],
         "correct": "C", "explanation": "You cannot add a str and an int; convert one of them first.", "concept": "type conversion"},
        {"type": "short", "prompt": "Which built-in function tells you the type of a value?", "correct": "type",
         "accepted": ["type()", "type(x)"], "explanation": "type(x) returns the type of x.", "concept": "type()"},
    ],
    1: [
        {"type": "mcq", "prompt": "fruits = ['apple', 'pear', 'kiwi']. What is fruits[1]?", "options": ["apple", "pear", "kiwi"],
         "correct": "pear", "explanation": "Indexing starts at 0, so index 1 is the second item.", "concept": "list indexing"},
        {"type": "short", "prompt": "Which list method adds one item to the end of a list?", "correct": "append",
         "accepted": ["append()", ".append", "list.append"], "explanation": "list.append(x) adds x at the end.", "concept": "list methods"},
    ],
}


class Command(BaseCommand):
    help = "Seed a demo instructor, class, lessons, quizzes and student."

    def add_arguments(self, parser):
        parser.add_argument("--base-url", default=settings.PUBLIC_BASE_URL or "http://localhost:8000")
        parser.add_argument("--username", default="demo")
        parser.add_argument("--password", default=os.environ.get("DEMO_INSTRUCTOR_PASSWORD", "demo-pass-123"))

    @transaction.atomic
    def handle(self, *args, base_url, username, password, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": "demo@example.com", "is_staff": True})
        if created:
            user.set_password(password)
            user.save()
        user.groups.add(ensure_instructors_group())
        instructor, _ = Instructor.objects.get_or_create(user=user, defaults={"display_name": "Demo Instructor"})

        course = Course.objects.filter(join_code=DEMO_CODE).first()
        if course is None:
            course = Course(instructor=instructor, title="Intro to Python", description="A 3-lesson demo class.")
            course.join_code = DEMO_CODE
            course.save()
            for i, data in enumerate(LESSONS, start=1):
                lesson = Lesson.objects.create(course=course, order=i, **data)
                for q_index, questions in QUIZZES.items():
                    if q_index == i - 1:
                        quiz = Quiz.objects.create(course=course, lesson=lesson, title=f"{lesson.title} quiz")
                        for n, q in enumerate(questions, start=1):
                            Question.objects.create(
                                quiz=quiz,
                                order=n,
                                type=q["type"],
                                prompt=q["prompt"],
                                options_json=q.get("options", []),
                                correct_answer=q["correct"],
                                accepted_answers_json=q.get("accepted", []),
                                explanation=q["explanation"],
                                concept=q["concept"],
                            )
            self.stdout.write(self.style.SUCCESS(f"Created class '{course.title}' (join code {DEMO_CODE})."))
        else:
            self.stdout.write("Demo class already exists.")

        enrollment = Enrollment.objects.filter(course=course, student__email="student@example.com").first()
        if enrollment is None:
            enrollment, raw = enrollments.join(course, name="Demo Student", email="student@example.com")
        else:
            raw = tokens.assign_new_token(enrollment)

        base = base_url.rstrip("/")
        self.stdout.write("")
        self.stdout.write(f"Instructor login : {base}/admin/  (user '{username}'" + (f", password '{password}')" if created else ", existing password)"))
        self.stdout.write(f"Invite link      : {base}/join/{DEMO_CODE}/")
        self.stdout.write(f"Demo student MCP : {base}/s/{raw}/mcp")
        self.stdout.write(self.style.WARNING("The demo student URL changes every time this command runs."))
