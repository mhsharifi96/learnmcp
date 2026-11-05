"""Rebuild a class as a full English course: placement test first, then A1–C2.

Lessons are written as short prompts (the student's AI builds the lesson plan) and every quiz is
AI-generated. Some lessons ask the student to answer by voice message.

    python manage.py build_english_course --join-code MM4EM8FX [--keep-existing]

WARNING: by default this deletes the class's existing lessons and quizzes (and their attempts).
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from learn.models import Course, Lesson, Quiz

TITLE = "English — placement test + A1 to C2"
DESCRIPTION = (
    "Start with the placement test (lesson 1). It tells you your level and which lesson to start from. "
    "Each level has 20 key words and one grammar + speaking lesson. Some lessons ask you to answer by voice.\n"
    "اول آزمون تعیین سطح (درس ۱) را بدهید؛ بعد از سطح خودتان ادامه دهید."
)

VOICE = (
    "Speaking practice: at the marked points ask the student to answer with a VOICE message (the microphone "
    "button in the Claude or ChatGPT app) instead of typing. If they can't use voice, let them type. "
    "Then give short feedback on grammar, word choice and fluency, and model a better version."
)

PERSIAN = (
    "The student is most likely a Persian speaker. Explain in simple English at their level; use a short "
    "Persian hint only if they are stuck. Watch for typical Persian-speaker mistakes (articles a/the, "
    "he/she confusion, word order, missing -s)."
)

PLACEMENT = {
    "title": "Placement test — start here",
    "brief": (
        "This is the placement test, not a normal lesson. Greet the student, explain in one short paragraph "
        "(English + one Persian line) that this test finds their level (A1–C2) so they can start at the right "
        "lesson, then start the placement quiz right away."
    ),
    "objectives": "Find the student's level (A1, A2, B1, B2, C1 or C2)\nRecommend the lesson to start from",
    "teaching_notes": (
        PERSIAN + " After the quiz, tell the student their level (A1–C2) with one sentence of reasons, "
        "and give them the exact lesson to start from (look it up with list_my_courses: the first lesson of "
        "that level). If they are between two levels, choose the lower one."
    ),
    "quiz": {
        "title": "Placement quiz",
        "count": 15,
        "prompt": (
            "Adaptive English placement test, 15 questions, getting harder step by step: questions 1–2 A1, "
            "3–4 A2, 5–7 B1, 8–10 B2, 11–12 C1, 13 C2. Mix grammar, vocabulary and reading (one short "
            "sentence or two). Mostly multiple choice with 4 options. If the student misses two questions in "
            "a row at a level, stay at that level instead of going higher. "
            "Question 14: ask the student to send a VOICE message (30–60 seconds) introducing themselves and "
            "their reasons for learning English; judge it as correct if it is clearly at or above the level "
            "reached so far. Question 15: a short writing task (2–3 sentences about their last weekend); judge "
            "it the same way. In the explanation field of every answer write the CEFR level of that question."
        ),
    },
}

LEVELS = [
    {
        "level": "A1",
        "words_brief": (
            "A1 beginners: teach 20 very common everyday words in 4 small groups of 5: greetings (hello, "
            "goodbye, please, thank you, sorry), family (mother, father, brother, sister, friend), food and "
            "drink (water, bread, tea, apple, rice), and everyday things (house, car, phone, book, money). "
            "For each word give the meaning, a very simple example sentence and the pronunciation."
        ),
        "words_voice": "After each group, ask the student to say the 5 words and one example sentence by voice.",
        "grammar_title": "A1 · Introducing yourself (to be, I/you/he/she)",
        "grammar_brief": (
            "A1: the verb 'to be' (am/is/are) with I, you, he, she, it, we, they; positive, negative and questions. "
            "Use it to introduce yourself: name, age, city, job. Use very short sentences."
        ),
        "grammar_voice": "End with a VOICE task: the student introduces themselves in 4–5 sentences.",
    },
    {
        "level": "A2",
        "words_brief": (
            "A2: teach 20 useful words for daily life in 4 groups of 5: shopping (buy, price, cheap, expensive, "
            "shop), travel (ticket, station, airport, hotel, trip), time (yesterday, tomorrow, always, never, "
            "weekend), and verbs (go, come, take, make, need). Give meaning, an example sentence and pronunciation."
        ),
        "words_voice": "Ask the student to make one sentence by voice with any 3 words from each group.",
        "grammar_title": "A2 · Past simple: talking about last weekend",
        "grammar_brief": (
            "A2: past simple, regular (-ed) and common irregular verbs (go/went, have/had, see/saw, eat/ate, "
            "buy/bought); negatives and questions with did. Practise talking about last weekend."
        ),
        "grammar_voice": "End with a VOICE task: the student describes their last weekend in 5–6 sentences.",
    },
    {
        "level": "B1",
        "words_brief": (
            "B1: teach 20 words about work, study and feelings in 4 groups of 5: work (colleague, salary, "
            "interview, deadline, career), study (improve, practise, mistake, progress, goal), feelings (worried, "
            "proud, disappointed, excited, nervous), and linking words (however, although, because of, so that, "
            "instead). Give meaning, example and a common collocation."
        ),
        "words_voice": "Ask the student to talk by voice for 30 seconds about their job or studies using 5 of the words.",
        "grammar_title": "B1 · Present perfect: experiences and changes",
        "grammar_brief": (
            "B1: present perfect (have/has + past participle) for experiences (ever/never), recent changes "
            "(just/already/yet) and for/since; contrast with past simple."
        ),
        "grammar_voice": (
            "End with a VOICE task: the student talks about something interesting they have done in their life "
            "(1 minute)."
        ),
    },
    {
        "level": "B2",
        "words_brief": (
            "B2: teach 20 words and phrases for opinions and discussion in 4 groups of 5: phrasal verbs (bring up, "
            "figure out, put off, come across, turn down), opinion language (in my view, I'd argue that, on the "
            "other hand, it depends on, to be fair), abstract nouns (issue, benefit, drawback, impact, trend), and "
            "adjectives (reliable, significant, controversial, efficient, harmful)."
        ),
        "words_voice": "Ask the student to give a short voice opinion on a topic you choose, using 5 of the phrases.",
        "grammar_title": "B2 · Conditionals: real, unreal and past",
        "grammar_brief": (
            "B2: first, second and third conditionals and mixed conditionals; 'unless', 'as long as', "
            "'I wish / If only'. Use real-life examples."
        ),
        "grammar_voice": (
            "End with a VOICE task: 'If you could live in any country for a year, where and why?' (1 minute)."
        ),
    },
    {
        "level": "C1",
        "words_brief": (
            "C1: teach 20 advanced words and collocations in 4 groups of 5: academic verbs (undermine, "
            "facilitate, outweigh, acknowledge, sustain), collocations (pose a threat, draw a conclusion, "
            "bear in mind, raise awareness, meet a demand), hedging (arguably, to some extent, it would seem, "
            "presumably, by and large), and precise adjectives (meticulous, inevitable, profound, viable, "
            "ambiguous). Focus on register and natural use."
        ),
        "words_voice": "Ask the student to explain a complex topic from their field by voice (1 minute) using 5 items.",
        "grammar_title": "C1 · Advanced structures for emphasis",
        "grammar_brief": (
            "C1: inversion for emphasis (Never have I…, Not only… but also, Hardly… when), cleft sentences "
            "(What I need is…, It was… that…), and participle clauses. Show formal vs informal use."
        ),
        "grammar_voice": "End with a VOICE task: a 1–2 minute mini-presentation using at least two of the structures.",
    },
    {
        "level": "C2",
        "words_brief": (
            "C2: teach 20 idioms and nuanced expressions in 4 groups of 5: idioms (a blessing in disguise, cut "
            "corners, the elephant in the room, on the fence, a double-edged sword), near-synonyms with nuance "
            "(reluctant/hesitant, notorious/famous, frugal/stingy, assertive/aggressive, candid/blunt), formal "
            "linkers (notwithstanding, insofar as, albeit, hence, whereby), and register shifts (informal ↔ formal "
            "pairs). Discuss tone and connotation."
        ),
        "words_voice": "Ask the student to tell a short story by voice that naturally uses 3 idioms.",
        "grammar_title": "C2 · Style, nuance and argument",
        "grammar_brief": (
            "C2: building a persuasive argument: concession and counter-argument, nominalisation, "
            "subtle modality (might well, could conceivably, is bound to), and editing for concise, natural style."
        ),
        "grammar_voice": (
            "End with a VOICE task: a 2-minute argument for or against a statement you give, then discuss how to "
            "make it more persuasive."
        ),
    },
]


def _lessons():
    yield PLACEMENT
    for lv in LEVELS:
        level = lv["level"]
        yield {
            "title": f"{level} · 20 key words",
            "brief": lv["words_brief"],
            "objectives": f"Learn and use 20 {level} words\nPronounce them correctly\nUse them in your own sentences",
            "teaching_notes": PERSIAN + " " + VOICE + " " + lv["words_voice"],
            "quiz": {
                "title": f"{level} words quiz",
                "count": 8,
                "prompt": (
                    f"8 questions on the 20 {level} words of this lesson: meaning, gap-fill and choosing the right "
                    "word; mostly multiple choice with 4 options, 2 short-answer gap-fills. One question per "
                    "word group at least. Last question: ask the student to answer by VOICE using two of the words "
                    "in a sentence, and judge whether they used them correctly."
                ),
            },
        }
        yield {
            "title": lv["grammar_title"],
            "brief": lv["grammar_brief"],
            "objectives": f"Understand the {level} grammar point\nUse it correctly in speaking and writing",
            "teaching_notes": PERSIAN + " " + VOICE + " " + lv["grammar_voice"],
            "quiz": {
                "title": f"{level} grammar quiz",
                "count": 8,
                "prompt": (
                    f"8 questions at {level} level on this lesson's grammar point: 5 multiple choice (4 options), "
                    "2 short-answer sentence corrections, and a final VOICE question where the student says two "
                    "sentences using the structure; judge them fairly for this level."
                ),
            },
        }


class Command(BaseCommand):
    help = "Rebuild a class as an English course (placement test + A1–C2) with AI lessons and quizzes."

    def add_arguments(self, parser):
        parser.add_argument("--join-code", required=True)
        parser.add_argument("--keep-existing", action="store_true", help="Do not delete existing lessons/quizzes.")

    @transaction.atomic
    def handle(self, *args, join_code, keep_existing, **options):
        course = Course.objects.filter(join_code=join_code.upper()).first()
        if course is None:
            raise CommandError(f"No class with join code {join_code}.")
        if not keep_existing:
            course.quizzes.all().delete()
            course.lessons.all().delete()
        start = (course.lessons.order_by("-order").values_list("order", flat=True).first() or 0) + 1

        course.title = TITLE
        course.description = DESCRIPTION
        course.save(update_fields=["title", "description"])

        for i, data in enumerate(_lessons()):
            lesson = Lesson(
                course=course,
                order=start + i,
                title=data["title"],
                brief=data["brief"],
                objectives=data["objectives"],
                teaching_notes=data["teaching_notes"],
            )
            lesson.full_clean()
            lesson.save()
            q = data["quiz"]
            quiz = Quiz(
                course=course, lesson=lesson, title=q["title"], mode=Quiz.AI, prompt=q["prompt"],
                ai_question_count=q["count"],
            )
            quiz.full_clean()
            quiz.save()
        self.stdout.write(
            self.style.SUCCESS(f"'{course.title}': {course.lessons.count()} lessons, {course.quizzes.count()} quizzes.")
        )
