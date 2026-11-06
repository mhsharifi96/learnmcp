"""More sample English classes for seed_samples (Persian-speaking learners)."""

from learn.models import Question, Quiz

from .commands.build_english_course import PERSIAN


def mcq(prompt, options, correct, explanation="", concept=""):
    return {"type": Question.MCQ, "prompt": prompt, "options": options, "correct": correct,
            "explanation": explanation, "concept": concept}


def short(prompt, correct, accepted=(), explanation="", concept=""):
    return {"type": Question.SHORT, "prompt": prompt, "correct": correct, "accepted": list(accepted),
            "explanation": explanation, "concept": concept}


ENGLISH_CLASSES = [
    # ------------------------------------------------------------------ IELTS speaking
    {
        "title": "IELTS Speaking: آمادگی آیلتس اسپیکینگ",
        "description": (
            "آمادگی بخش Speaking آزمون آیلتس با هوش مصنوعی: سؤال‌های Part 1، کیو کارت Part 2 و بحث Part 3. "
            "با ویس جواب می‌دهید و بازخورد روانی، گرامر، واژگان و تلفظ می‌گیرید. مناسب سطح B1 تا B2 برای نمرهٔ ۶ تا ۷."
        ),
        "lessons": [
            {
                "title": "Part 1: short answers about yourself",
                "kind": "speaking",
                "objectives": "Answer Part 1 questions in 2-3 sentences\nExtend answers with a reason and an example",
                "brief": (
                    "B1-B2 IELTS Speaking Part 1. Topics: home town, work or study, free time, food, weather. "
                    "Teach the answer + reason + example pattern. Ask 8 questions one at a time, the student "
                    "answers by voice; give feedback on length, fluency and one grammar or word point each time."
                ),
                "teaching_notes": PERSIAN + " Discourage one-word answers and memorised speeches.",
            },
            {
                "title": "Part 2: the cue card in two minutes",
                "kind": "speaking",
                "objectives": "Plan a cue-card answer in one minute\nSpeak for 1.5-2 minutes using the bullet points",
                "brief": (
                    "B1-B2 IELTS Speaking Part 2. Show how to make 1-minute notes (who, what, when, why, feeling) "
                    "and link ideas (First of all, What I remember most, The reason why…). Give 3 cue cards "
                    "(a person you admire, a place you visited, a skill you learned); student records a long answer."
                ),
                "teaching_notes": PERSIAN + " Note pauses, repetition and tense mistakes in past stories.",
            },
            {
                "title": "Part 3: giving and supporting opinions",
                "kind": "speaking",
                "objectives": "Give opinions with reasons\nCompare past and present, and talk about the future",
                "brief": (
                    "B2 IELTS Speaking Part 3: abstract discussion questions (technology, education, cities). "
                    "Teach opinion phrases (I'd say that…, It depends on…, On the other hand…) and hedging. "
                    "6 questions, one at a time, with a model band-7 answer after each student answer."
                ),
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Fluency, fillers and pronunciation for the exam",
                "kind": "pronunciation",
                "objectives": "Use natural fillers instead of silence\nStress key words and keep a steady rhythm",
                "brief": (
                    "B1-B2: how fluency and pronunciation are scored. Natural fillers (Well, Let me think, "
                    "That's an interesting question), word stress, sentence stress and chunking. Read-aloud "
                    "practice with 5 sentences, then 3 quick questions answered by voice."
                ),
                "teaching_notes": PERSIAN + " Common Persian-speaker issues: adding a vowel before s+consonant (\"estudent\"), v/w, th.",
            },
        ],
        "quizzes": [
            {
                "title": "IELTS speaking phrases quiz",
                "lesson": 3,
                "questions": [
                    mcq("Which answer to \"Do you like cooking?\" is best for Part 1?",
                        ["Yes.", "Yes, I do.",
                         "Yes, I do, especially on weekends, because it helps me relax after a busy week.",
                         "Cooking is an activity of preparing food."], "C",
                        "Answer + reason + detail: short but extended.", "extending answers"),
                    mcq("Which phrase gives a balanced opinion in Part 3?",
                        ["I'm 100% sure that…", "On the other hand, some people argue that…",
                         "Everybody knows that…", "No idea."], "B",
                        "Showing both sides is typical of higher bands.", "opinion phrases"),
                    short("How long should you speak in Part 2 (in minutes)?", "2", ["two", "1-2", "2 minutes"],
                          "Up to 2 minutes; the examiner stops you.", "part 2 timing"),
                    mcq("Which filler is most natural when you need a second to think?",
                        ["Hmmmmmm…", "Let me think about that for a moment.", "I don't know.", "Next question."], "B",
                        "Natural fillers keep you fluent.", "fillers"),
                ],
            },
            {
                "title": "Mock IELTS speaking test (AI)",
                "lesson": 4,
                "mode": Quiz.AI,
                "count": 6,
                "prompt": (
                    "A short mock IELTS Speaking test, answered by voice: 3 Part 1 questions, 1 Part 2 cue card "
                    "(ask the student to speak for up to 2 minutes), 2 Part 3 questions on the same theme. "
                    "After each answer give an estimated band for fluency, vocabulary, grammar and pronunciation "
                    "with one concrete tip. Mark an answer ok if it is band 6 or higher."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Travel English
    {
        "title": "English for Travel: انگلیسی سفر",
        "description": (
            "انگلیسی کاربردی برای سفر خارجی: فرودگاه، هتل، رستوران، پرسیدن آدرس و موقعیت‌های اضطراری. "
            "با نقش‌آفرینی (role-play) با هوش مصنوعی تمرین می‌کنید. مناسب سطح A2 و مبتدی."
        ),
        "lessons": [
            {
                "title": "At the airport",
                "kind": "conversation",
                "objectives": "Check in and go through passport control\nUnderstand boarding announcements",
                "brief": (
                    "A2 role-play at the airport: check-in desk (window or aisle seat, baggage), security and "
                    "passport control (purpose of visit, how long you stay). Useful phrases first, then the AI "
                    "plays the staff."
                ),
                "teaching_notes": PERSIAN,
            },
            {
                "title": "At the hotel",
                "kind": "conversation",
                "objectives": "Check in with a booking\nAsk for help and report a problem in the room",
                "brief": (
                    "A2 role-play at a hotel reception: checking in (I have a reservation under…), asking about "
                    "breakfast and Wi-Fi, and complaining politely (The air conditioning isn't working)."
                ),
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Ordering food at a restaurant",
                "kind": "conversation",
                "objectives": "Order politely with I'd like / Could I have\nAsk about ingredients and pay the bill",
                "brief": (
                    "A2: ordering in a restaurant: a table for two, the menu, I'd like…, Could I have…, Is there "
                    "any meat in this?, Can we have the bill, please? Then a role-play with the AI as the waiter."
                ),
                "teaching_notes": PERSIAN + " Correct direct forms like \"Give me…\" to polite ones.",
            },
            {
                "title": "Asking for directions and getting around",
                "kind": "conversation",
                "objectives": "Ask for and understand directions\nBuy a ticket for public transport",
                "brief": (
                    "A2: asking the way (Excuse me, how do I get to…?), understanding directions (turn left, go "
                    "straight, it's opposite…), and buying a metro or bus ticket. Role-play on a simple map described in text."
                ),
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Emergencies and health problems",
                "kind": "vocabulary",
                "objectives": "Explain a health problem at a pharmacy\nAsk for help when you lose something",
                "brief": (
                    "A2 vocabulary for emergencies: at the pharmacy (I have a headache / a fever / a sore throat), "
                    "lost passport or bag, calling for help. 15 words and phrases with practice."
                ),
                "teaching_notes": PERSIAN,
            },
        ],
        "quizzes": [
            {
                "title": "Travel English quiz",
                "lesson": 3,
                "questions": [
                    mcq("At check-in, the agent asks \"Window or aisle?\". They mean:",
                        ["Your seat", "Your bag", "Your meal", "Your ticket price"], "A",
                        "Window or aisle seat on the plane.", "airport"),
                    mcq("The most polite way to order is:",
                        ["Give me a coffee.", "I want coffee.", "I'd like a coffee, please.", "Coffee!"], "C",
                        "«I'd like…, please» is polite.", "ordering"),
                    short("Complete: \"Can we have the ___, please?\" (you want to pay)", "bill", ["check"],
                          "British «bill», American «check».", "restaurant"),
                    mcq("\"It's opposite the bank\" means it is:",
                        ["next to the bank", "across from the bank", "behind the bank", "inside the bank"], "B",
                        "Opposite = on the other side of the street.", "directions"),
                    short("Complete: \"I have a ___ throat.\" (it hurts when you swallow)", "sore",
                          explanation="A sore throat.", concept="health"),
                ],
            },
            {
                "title": "Travel role-play check (AI)",
                "lesson": 5,
                "mode": Quiz.AI,
                "count": 5,
                "prompt": (
                    "5 short travel situations for an A2 learner (airport, hotel, restaurant, directions, "
                    "pharmacy). Describe each situation in one line and ask what the student would say. "
                    "Accept any polite, understandable answer; show a natural model sentence after each."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Grammar
    {
        "title": "Essential English Grammar: گرامر ضروری انگلیسی",
        "description": (
            "گرامر پرکاربرد انگلیسی برای سطح A2 تا B1 با توضیح ساده به فارسی و تمرین زیاد: زمان حال، گذشته و "
            "حال کامل، آینده، حرف تعریف a/the و جمله‌های شرطی. هوش مصنوعی اشتباه‌های رایج فارسی‌زبان‌ها را تصحیح می‌کند."
        ),
        "lessons": [
            {
                "title": "Present simple vs present continuous",
                "kind": "grammar",
                "objectives": "Choose between habits and actions happening now\nUse stative verbs correctly (like, know, want)",
                "brief": "A2: present simple (habits, facts) vs present continuous (now, temporary). Stative verbs. Time words: usually, now, these days.",
                "teaching_notes": PERSIAN + " Persian uses one present form; expect \"I am go\" and \"I am knowing\".",
            },
            {
                "title": "Past simple vs present perfect",
                "kind": "grammar",
                "objectives": "Use past simple for finished time\nUse present perfect for experience and unfinished time",
                "brief": "B1: past simple (yesterday, in 2020) vs present perfect (ever, never, already, yet, for, since). Irregular past participles.",
                "teaching_notes": PERSIAN + " Typical error: \"I have seen him yesterday\".",
            },
            {
                "title": "Talking about the future",
                "kind": "grammar",
                "objectives": "Choose will, going to or present continuous for the future",
                "brief": "A2-B1: will (decisions now, predictions), going to (plans, evidence), present continuous (arrangements).",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Articles: a, an, the or nothing",
                "kind": "grammar",
                "objectives": "Use a/an for one of many, the for a specific thing\nKnow when to use no article",
                "brief": "A2-B1: a/an, the and zero article, with countable/uncountable nouns and common fixed uses (the sun, go to school).",
                "teaching_notes": PERSIAN + " Persian has no articles; this is the most common error. Give many short examples.",
            },
            {
                "title": "Conditionals: if sentences",
                "kind": "grammar",
                "objectives": "Use zero, first and second conditionals",
                "brief": "B1: zero (facts), first (real future) and second (imaginary) conditionals. If I were you… for advice.",
                "teaching_notes": PERSIAN + " Watch for \"If it will rain\".",
            },
        ],
        "quizzes": [
            {
                "title": "Grammar check: tenses",
                "lesson": 2,
                "questions": [
                    mcq("She ___ to work by bus every day.", ["go", "goes", "is going", "going"], "B",
                        "Habit + he/she/it: present simple with -s.", "present simple"),
                    mcq("Listen! The baby ___.", ["cries", "cry", "is crying", "has cried"], "C",
                        "Happening now: present continuous.", "present continuous"),
                    mcq("I ___ him yesterday.", ["have seen", "saw", "see", "have saw"], "B",
                        "Finished time (yesterday): past simple.", "past simple vs present perfect"),
                    mcq("Have you ever ___ sushi?", ["eat", "ate", "eaten", "eating"], "C",
                        "Present perfect: have + past participle.", "present perfect"),
                    short("Complete with the correct form: \"I ___ (live) here since 2019.\"", "have lived",
                          ["'ve lived", "have been living"], "since + present perfect.", "since/for"),
                ],
            },
            {
                "title": "Grammar check: articles and conditionals",
                "lesson": 5,
                "questions": [
                    mcq("I saw ___ elephant at the zoo.", ["a", "an", "the", "—"], "B",
                        "«an» before a vowel sound.", "articles"),
                    mcq("___ sun rises in the east.", ["A", "An", "The", "—"], "C",
                        "Only one sun: «the».", "articles"),
                    mcq("If it ___ tomorrow, we will stay home.", ["will rain", "rains", "rained", "rain"], "B",
                        "First conditional: if + present, will + verb.", "first conditional"),
                    mcq("If I ___ you, I would study more.", ["am", "was", "were", "be"], "C",
                        "Advice: If I were you…", "second conditional"),
                ],
            },
            {
                "title": "Correct the sentence (AI)",
                "lesson": 4,
                "mode": Quiz.AI,
                "count": 8,
                "prompt": (
                    "8 sentences with one typical Persian-speaker grammar mistake each (tenses, articles, "
                    "conditionals, stative verbs). The student rewrites the sentence correctly. A2-B1 level. "
                    "Explain the rule in one line after each answer."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Vocabulary
    {
        "title": "Everyday English Vocabulary: واژگان روزمره انگلیسی",
        "description": (
            "یادگیری لغات پرکاربرد انگلیسی در گروه‌های موضوعی با مثال و تکرار فاصله‌دار: خانه، کار، احساسات، "
            "فعل‌های دوکلمه‌ای (phrasal verbs) و همنشین‌ها (collocations). مناسب سطح A2 تا B1."
        ),
        "lessons": [
            {
                "title": "Home and daily routine",
                "kind": "vocabulary",
                "objectives": "Learn 20 words for home and daily routine\nDescribe your day",
                "brief": "A2: 20 words: rooms and furniture, daily actions (wake up, take a shower, do the dishes). End: describe your morning in 4 sentences.",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Work and study",
                "kind": "vocabulary",
                "objectives": "Learn 20 words for jobs, the office and university",
                "brief": "A2-B1: jobs, workplace and study words (colleague, deadline, assignment, apply for, be in charge of).",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Feelings and personality",
                "kind": "vocabulary",
                "objectives": "Describe feelings precisely\nUse -ed and -ing adjectives correctly",
                "brief": "B1: feelings (anxious, relieved, disappointed), personality (outgoing, reliable) and -ed/-ing pairs (bored/boring).",
                "teaching_notes": PERSIAN + " Typical error: \"I am boring\" meaning «حوصله‌ام سر رفته».",
            },
            {
                "title": "Common phrasal verbs",
                "kind": "vocabulary",
                "objectives": "Understand and use 15 common phrasal verbs",
                "brief": "B1: 15 phrasal verbs in context: look for, give up, find out, turn on/off, pick up, run out of, get on with, put off.",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Collocations: words that go together",
                "kind": "vocabulary",
                "objectives": "Use make/do, have/take and other common collocations",
                "brief": "B1: make a decision, do homework, take a photo, have a break, heavy rain, strong coffee. Contrast with Persian word-for-word choices.",
                "teaching_notes": PERSIAN + " Persian «کردن» often becomes the wrong verb: \"do a mistake\".",
            },
        ],
        "quizzes": [
            {
                "title": "Vocabulary quiz",
                "lesson": 5,
                "questions": [
                    mcq("The film was very long and I was ___.", ["boring", "bored", "bore", "bores"], "B",
                        "-ed for how you feel.", "-ed/-ing adjectives"),
                    mcq("Don't ___ up! You can do it.", ["give", "take", "look", "put"], "A",
                        "give up = stop trying.", "phrasal verbs"),
                    mcq("Which is correct?", ["do a mistake", "make a mistake", "take a mistake", "have a mistake"], "B",
                        "make a mistake.", "collocations"),
                    short("I need to ___ out what time the train leaves. (discover information)", "find",
                          explanation="find out = discover.", concept="phrasal verbs"),
                    mcq("A person you work with is a:", ["classmate", "colleague", "neighbour", "relative"], "B",
                        "colleague = co-worker.", "work vocabulary"),
                ],
            },
            {
                "title": "Word review (AI)",
                "lesson": 3,
                "mode": Quiz.AI,
                "count": 8,
                "prompt": (
                    "8 quick recall questions mixing the class vocabulary (home, work, feelings, phrasal verbs, "
                    "collocations): give the Persian meaning and ask for the English word, or a sentence with a gap. "
                    "A2-B1 level, one at a time."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Pronunciation
    {
        "title": "English Pronunciation for Persian Speakers: تلفظ انگلیسی",
        "description": (
            "تلفظ انگلیسی مخصوص فارسی‌زبان‌ها: صداهای th، تفاوت v و w، مصوت‌های کوتاه و بلند، استرس کلمه و "
            "خوشه‌های صامت (بدون «اِ» اضافه مثل estudent). با ویس تمرین می‌کنید و هوش مصنوعی بازخورد می‌دهد."
        ),
        "lessons": [
            {
                "title": "The th sounds",
                "kind": "pronunciation",
                "objectives": "Pronounce /θ/ (think) and /ð/ (this)\nHear the difference from /t/, /s/, /d/, /z/",
                "brief": "A2-B1: tongue between the teeth for /θ/ and /ð/. Minimal pairs: think/sink, three/tree, they/day. Read-aloud practice by voice.",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "V and W",
                "kind": "pronunciation",
                "objectives": "Pronounce /w/ with rounded lips, not as /v/",
                "brief": "A2-B1: /v/ (teeth on lip) vs /w/ (round lips). Minimal pairs: vest/west, vine/wine, very/wary.",
                "teaching_notes": PERSIAN + " Persian «و» is closer to /v/, so \"wine\" often sounds like \"vine\".",
            },
            {
                "title": "Short and long vowels",
                "kind": "pronunciation",
                "objectives": "Tell /ɪ/ from /iː/ and /ʊ/ from /uː/",
                "brief": "B1: ship/sheep, live/leave, full/fool. Listening and speaking practice with sentences.",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Consonant clusters without an extra vowel",
                "kind": "pronunciation",
                "objectives": "Say words starting with s + consonant without adding «اِ»\nPronounce word endings clearly",
                "brief": "B1: school, student, street, spring (not eschool, estudent). Final clusters: asked, months, texts.",
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Word stress and sentence rhythm",
                "kind": "pronunciation",
                "objectives": "Stress the right syllable in common words\nStress key words in a sentence",
                "brief": "B1: PHOtograph, phoTOgraphy, photoGRAphic; nouns vs verbs (REcord / reCORD); content words vs function words.",
                "teaching_notes": PERSIAN + " Persian stress is often on the last syllable; English is different.",
            },
        ],
        "quizzes": [
            {
                "title": "Pronunciation quiz",
                "lesson": 5,
                "questions": [
                    mcq("Which word starts with the same sound as \"think\"?", ["this", "three", "tree", "sink"], "B",
                        "three /θ/; this has /ð/.", "th sounds"),
                    mcq("In \"photography\", which syllable is stressed?", ["PHO", "TO", "GRA", "PHY"], "B",
                        "phoTOgraphy.", "word stress"),
                    mcq("Which pair is a minimal pair for /v/ and /w/?", ["vest / west", "very / berry", "wine / line", "vote / boat"], "A",
                        "vest / west differ only by /v/ and /w/.", "v and w"),
                    mcq("How many syllables does \"school\" have?", ["1", "2", "3", "4"], "A",
                        "One syllable; don't add «اِ» (eschool).", "consonant clusters"),
                ],
            },
            {
                "title": "Read-aloud check (AI)",
                "lesson": 4,
                "mode": Quiz.AI,
                "count": 5,
                "prompt": (
                    "5 short sentences to read aloud by voice, each packed with one target sound (th, v/w, "
                    "short/long vowels, s-clusters, word stress). After each recording, say which words were "
                    "unclear and how to fix them. Mark ok if the target sound was clear."
                ),
            },
        ],
    },
]
