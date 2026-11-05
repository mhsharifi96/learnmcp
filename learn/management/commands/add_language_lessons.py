"""Add skill lessons to an English course built by build_english_course, without deleting anything.

For each level A1–C2 it adds four lessons right after that level's existing lessons:
Persian → English translation + grammar, role-play, reading and writing. It also tags the
existing lessons with their type (vocabulary, grammar). Running it twice adds nothing new.

    python manage.py add_language_lessons --join-code MM4EM8FX [--dry-run]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learn.models import Course, Lesson

from .build_english_course import PERSIAN, VOICE

SKILLS = {
    "A1": {
        "translation": "to be, have got, present simple, there is/are, this/that, simple yes/no questions",
        "conversation": "introducing yourself to a new classmate, then buying fruit and bread in a small shop",
        "reading": "a 90-word text about a person's family and daily routine",
        "writing": "a 40-60 word message introducing yourself (name, age, city, job/study, hobbies)",
    },
    "A2": {
        "translation": "past simple (regular and irregular), going to, comparatives, can/must, countable/uncountable",
        "conversation": "ordering in a café, then asking for and following directions in a city",
        "reading": "a 150-word text about a weekend trip, with times and places",
        "writing": "an 80-word email to a friend about last weekend",
    },
    "B1": {
        "translation": "present perfect vs past simple, first and second conditionals, basic passive, used to",
        "conversation": "booking a doctor's appointment by phone, then complaining politely at a hotel reception",
        "reading": "a 250-word text about studying or working abroad",
        "writing": "a 120-150 word opinion paragraph with a clear reason and example",
    },
    "B2": {
        "translation": "mixed conditionals, reported speech, relative clauses, modals of deduction, wish/if only",
        "conversation": "a job interview for a role the student chooses; the AI is the interviewer",
        "reading": "a 400-word magazine article with an argument and some idioms",
        "writing": "a 180-word formal email of complaint with a request",
    },
    "C1": {
        "translation": "inversion, cleft sentences, advanced passives, participle clauses, hedging language",
        "conversation": "a business meeting where the student negotiates a deadline and budget",
        "reading": "an opinion article that needs inference about the writer's attitude",
        "writing": "a 250-word discursive essay with an introduction, two sides and a conclusion",
    },
    "C2": {
        "translation": "nuance and register: idioms, collocations, formal vs informal choices, concise style",
        "conversation": "a structured debate on a statement the AI proposes; the AI argues the other side",
        "reading": "a dense academic or literary extract with subtle meaning and figurative language",
        "writing": "a 300-word review or report in a precise, natural style",
    },
}

TEMPLATES = {
    "translation": {
        "title": "{level} · Persian → English + grammar",
        "brief": (
            "{level}: Persian-to-English translation practice. Give 10 Persian sentences, one at a time, that use "
            "{topic}. Start easy and get harder. The student translates; correct and explain the grammar behind "
            "each mistake."
        ),
        "objectives": "Translate {level} Persian sentences into natural English\nNotice and fix your grammar mistakes",
    },
    "conversation": {
        "title": "{level} · Role-play",
        "brief": "{level}: role-play: {topic}. Keep it at {level} level and give useful phrases first.",
        "objectives": "Take part in a real-life conversation at {level} level\nUse useful phrases naturally",
    },
    "reading": {
        "title": "{level} · Reading",
        "brief": "{level}: reading practice with {topic}. Pre-teach key words, then ask comprehension questions.",
        "objectives": "Understand the main idea and details of a {level} text\nLearn useful words from it",
    },
    "writing": {
        "title": "{level} · Writing",
        "brief": "{level}: writing task: {topic}. Give a short model first, then correct by error type.",
        "objectives": "Write a {level} text with a clear structure\nFix your own mistakes after feedback",
    },
}

LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]
SKILL_SUFFIXES = [tpl["title"].replace("{level} · ", "") for tpl in TEMPLATES.values()]


def _level(title: str) -> str | None:
    head = title.split("·")[0].strip()
    return head if head in LEVELS else None


class Command(BaseCommand):
    help = "Add translation, role-play, reading and writing lessons for each level of an English course."

    def add_arguments(self, parser):
        parser.add_argument("--join-code", required=True)
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, join_code: str, dry_run: bool = False, **options):
        course = Course.objects.filter(join_code=join_code.strip().upper()).first()
        if course is None:
            raise CommandError(f"No class with join code {join_code}.")
        existing = list(course.lessons.order_by("order", "id"))
        titles = {l.title for l in existing}

        tagged = 0
        for lesson in existing:
            if lesson.kind != "general":
                continue
            if "key words" in lesson.title:
                lesson.kind = "vocabulary"
            elif _level(lesson.title) and not any(lesson.title.endswith(suffix) for suffix in SKILL_SUFFIXES):
                lesson.kind = "grammar"
            else:
                continue
            tagged += 1

        ordered: list[Lesson] = []
        added = 0
        for i, lesson in enumerate(existing):
            ordered.append(lesson)
            level = _level(lesson.title)
            nxt = existing[i + 1] if i + 1 < len(existing) else None
            if level and (nxt is None or _level(nxt.title) != level):
                for kind, tpl in TEMPLATES.items():
                    title = tpl["title"].format(level=level)
                    if title in titles:
                        continue
                    topic = SKILLS[level][kind]
                    ordered.append(
                        Lesson(
                            course=course,
                            title=title,
                            kind=kind,
                            brief=tpl["brief"].format(level=level, topic=topic),
                            objectives=tpl["objectives"].format(level=level),
                            teaching_notes=PERSIAN + (" " + VOICE if kind == "conversation" else ""),
                        )
                    )
                    added += 1

        for n, lesson in enumerate(ordered, start=1):
            lesson.order = n
            lesson.full_clean()
            if not dry_run:
                lesson.save()
        if dry_run:
            transaction.set_rollback(True)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry run] ' if dry_run else ''}'{course.title}': added {added} lessons, tagged {tagged}, "
                f"{len(ordered)} lessons in total."
            )
        )
