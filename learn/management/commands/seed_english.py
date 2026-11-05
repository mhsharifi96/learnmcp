"""Create a sample English (A2) class with lessons and quizzes for an existing instructor.

    python manage.py seed_english --username mh
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learn.models import Course, Instructor, Lesson, Question, Quiz

TITLE = "Everyday English (A2) — sample"

LESSONS = [
    {
        "title": "Present simple vs present continuous",
        "objectives": (
            "Use the present simple for habits and facts\n"
            "Use the present continuous for actions happening now\n"
            "Recognise signal words (every day, usually, now, at the moment)"
        ),
        "content": (
            "Present simple = habits, routines and facts.\n"
            "  I work in an office. She drinks coffee every morning. Water boils at 100°C.\n"
            "  He/she/it adds -s: she works, he goes, it rains.\n"
            "  Negatives and questions use do/does: I don't like tea. Does she live here?\n"
            "  Signal words: always, usually, often, sometimes, never, every day.\n\n"
            "Present continuous = actions happening now or around now.\n"
            "  Form: am/is/are + verb-ing. I am reading. They are watching TV.\n"
            "  Signal words: now, right now, at the moment, today, this week.\n\n"
            "Some verbs are not usually used in the continuous: know, like, want, need, understand.\n"
            "  Say: I know the answer (not: I am knowing)."
        ),
        "teaching_notes": (
            "The student is likely a Persian speaker. Explain in simple English; use a short Persian hint only if "
            "they are stuck. Give personal examples (ask about their daily routine, then what they are doing now). "
            "Common mistakes: forgetting -s with he/she/it, and using the continuous with 'know' or 'want'."
        ),
    },
    {
        "title": "Past simple: regular and irregular verbs",
        "objectives": (
            "Form the past simple of regular verbs with -ed\n"
            "Use common irregular verbs (go, have, see, eat, buy)\n"
            "Make negatives and questions with did"
        ),
        "content": (
            "Past simple = finished actions in the past (yesterday, last week, in 2020, two days ago).\n\n"
            "Regular verbs add -ed: work → worked, play → played, study → studied, stop → stopped.\n\n"
            "Irregular verbs must be learned: go → went, have → had, see → saw, eat → ate, buy → bought, "
            "make → made, take → took, come → came.\n\n"
            "Negatives and questions use did + base verb:\n"
            "  I didn't go to work. (not: I didn't went)\n"
            "  Did you see the film? Yes, I did."
        ),
        "teaching_notes": (
            "Ask the student what they did yesterday or last weekend and correct gently. "
            "Typical mistake: using the past form after did/didn't ('Did you went?')."
        ),
    },
    {
        "title": "Prepositions of time: in, on, at",
        "objectives": "Choose in, on or at before times, days, months and years",
        "content": (
            "AT for clock times and some fixed expressions: at 7 o'clock, at noon, at night, at the weekend (UK).\n"
            "ON for days and dates: on Monday, on 5 May, on my birthday, on Friday evening.\n"
            "IN for months, years, seasons and parts of the day: in June, in 2024, in summer, in the morning.\n\n"
            "Tip: think big → small: IN (long periods) → ON (days) → AT (exact times)."
        ),
        "teaching_notes": (
            "Use the 'big to small' pyramid. Quick drill: give a time expression and let the student choose. "
            "Watch for 'in Monday' and 'at the morning'."
        ),
    },
]

QUIZZES = {
    1: [
        {"type": "mcq", "prompt": "She ___ to work by bus every day.",
         "options": ["go", "goes", "is going", "going"], "correct": "B",
         "explanation": "Habit + he/she/it → present simple with -s: she goes.", "concept": "present simple -s"},
        {"type": "mcq", "prompt": "Be quiet, please. The baby ___.",
         "options": ["sleeps", "is sleeping", "sleep", "slept"], "correct": "B",
         "explanation": "Happening now → present continuous: is sleeping.", "concept": "present continuous"},
        {"type": "mcq", "prompt": "Which sentence is correct?",
         "options": ["I am knowing the answer.", "I know the answer.", "I knows the answer.", "I knowing the answer."],
         "correct": "B", "explanation": "'Know' is a state verb, so we don't use it in the continuous.",
         "concept": "state verbs"},
        {"type": "short", "prompt": "Complete with the correct form of 'live': My parents ___ in Tehran.",
         "correct": "live", "accepted": [],
         "explanation": "Fact about the present, plural subject → live (no -s).", "concept": "present simple"},
    ],
    2: [
        {"type": "mcq", "prompt": "Yesterday I ___ a new phone.",
         "options": ["buyed", "buy", "bought", "buys"], "correct": "C",
         "explanation": "'Buy' is irregular: buy → bought.", "concept": "irregular verbs"},
        {"type": "mcq", "prompt": "Which question is correct?",
         "options": ["Did you went to the party?", "Did you go to the party?", "You did go to the party?",
                     "Went you to the party?"],
         "correct": "B", "explanation": "After did, use the base verb: Did you go…?", "concept": "did + base verb"},
        {"type": "short", "prompt": "Write the past simple of 'see'.", "correct": "saw", "accepted": [],
         "explanation": "see → saw (irregular).", "concept": "irregular verbs"},
        {"type": "short", "prompt": "Write the past simple of 'study'.", "correct": "studied", "accepted": [],
         "explanation": "Consonant + y → change y to i and add -ed: studied.", "concept": "regular -ed spelling"},
    ],
    3: [
        {"type": "mcq", "prompt": "The meeting starts ___ 9 o'clock.",
         "options": ["in", "on", "at"], "correct": "C",
         "explanation": "Exact clock time → at.", "concept": "at + time"},
        {"type": "mcq", "prompt": "My birthday is ___ March.",
         "options": ["in", "on", "at"], "correct": "A",
         "explanation": "Months → in.", "concept": "in + month"},
        {"type": "mcq", "prompt": "We have English class ___ Saturday.",
         "options": ["in", "on", "at"], "correct": "B",
         "explanation": "Days → on.", "concept": "on + day"},
        {"type": "short", "prompt": "Fill the gap with one word: I usually study ___ the evening.",
         "correct": "in", "accepted": [],
         "explanation": "Parts of the day → in the morning / afternoon / evening.", "concept": "in + part of day"},
    ],
}


class Command(BaseCommand):
    help = "Create a sample English (A2) class for an existing instructor."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Instructor's login username.")

    @transaction.atomic
    def handle(self, *args, username, **options):
        instructor = Instructor.objects.filter(user__username=username).first()
        if instructor is None:
            raise CommandError(f"No instructor with username '{username}'.")
        existing = Course.objects.filter(instructor=instructor, title=TITLE).first()
        if existing:
            self.stdout.write(f"Class already exists (join code {existing.join_code}).")
            return

        course = Course.objects.create(
            instructor=instructor,
            title=TITLE,
            description="A short sample class: present tenses, past simple and prepositions of time.",
        )
        for order, data in enumerate(LESSONS, start=1):
            lesson = Lesson.objects.create(course=course, order=order, **data)
            quiz = Quiz.objects.create(course=course, lesson=lesson, title=f"Quiz: {lesson.title}")
            for n, q in enumerate(QUIZZES[order], start=1):
                question = Question(
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
                question.full_clean()
                question.save()
        self.stdout.write(self.style.SUCCESS(f"Created '{course.title}' (join code {course.join_code})."))
