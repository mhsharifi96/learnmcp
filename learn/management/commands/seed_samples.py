"""Create sample classes for different uses on a demo instructor.

Six listed classes, each with 3-5 lessons and at least one quiz (instructor-written questions
graded by the server, and AI-written quizzes built from a prompt):

- Python programming basics (Persian)
- High-school math: algebra (Persian)
- Job-interview prep (Persian)
- Personal finance basics (Persian)
- Business email writing, Persian -> English (English lessons, Persian notes)
- University entrance exam prep: biology (Persian)
- English: IELTS speaking, travel, essential grammar, everyday vocabulary, pronunciation
  (in learn/management/english_samples.py)

Safe to run more than once: classes, lessons and quizzes are matched by title and never
overwritten, so instructor edits are kept. Questions are only added to quizzes created now.

    python manage.py seed_samples [--username demo] [--dry-run]
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from learn.apps import ensure_instructors_group
from learn.models import Course, Instructor, Lesson, Question, Quiz

from learn.management.english_samples import ENGLISH_CLASSES

from .build_english_course import PERSIAN

FA_TUTOR = (
    "دانش‌آموز فارسی‌زبان است. به فارسی ساده و دوستانه توضیح بده، اصطلاح‌های تخصصی را یک بار به انگلیسی هم بگو، "
    "هر بار فقط یک قدم جلو برو و بعد از هر بخش با یک سؤال کوتاه بفهم که مطلب را گرفته است."
)


def mcq(prompt, options, correct, explanation="", concept=""):
    return {"type": Question.MCQ, "prompt": prompt, "options": options, "correct": correct,
            "explanation": explanation, "concept": concept}


def short(prompt, correct, accepted=(), explanation="", concept=""):
    return {"type": Question.SHORT, "prompt": prompt, "correct": correct, "accepted": list(accepted),
            "explanation": explanation, "concept": concept}


CLASSES = [
    # ------------------------------------------------------------------ Python
    {
        "title": "مبانی برنامه‌نویسی پایتون",
        "description": (
            "شروع برنامه‌نویسی از صفر با پایتون: متغیرها، شرط‌ها، حلقه‌ها و تابع‌ها. "
            "هر درس با مثال‌های کوتاه و تمرین‌هایی که خودتان اجرا می‌کنید. مناسب دانش‌آموزان و دانشجویان بدون پیش‌زمینه."
        ),
        "lessons": [
            {
                "title": "متغیرها و انواع داده",
                "objectives": "ساختن متغیر و نام‌گذاری درست\nشناخت int، float، str و bool\nتبدیل نوع با int() و str()",
                "brief": (
                    "درس اول پایتون برای مبتدی کامل: متغیر چیست، انواع داده int, float, str, bool، تابع type() و "
                    "تبدیل نوع. با مثال‌های روزمره (سن، قیمت، اسم) و ۴ تمرین کوتاه که دانش‌آموز خودش تایپ می‌کند."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: جمع کردن رشته و عدد ('2' + 2). حتماً خطای TypeError را نشان بده.",
            },
            {
                "title": "شرط‌ها: if، elif و else",
                "objectives": "نوشتن شرط با عملگرهای مقایسه\nاستفاده از and، or و not\nفهم تورفتگی (indentation) در پایتون",
                "brief": (
                    "آموزش شرط‌ها در پایتون: عملگرهای مقایسه (== != < > <= >=)، if/elif/else، ترکیب شرط با and/or/not "
                    "و اهمیت تورفتگی. مثال: برنامه‌ای که نمره را می‌گیرد و «عالی/خوب/قبول/مردود» چاپ می‌کند."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: استفاده از = به جای == و فراموش کردن دونقطه (:) بعد از if.",
            },
            {
                "title": "حلقه‌ها: for و while",
                "objectives": "تکرار با for و range()\nحلقهٔ while و شرط پایان\nاستفاده از break و continue",
                "brief": (
                    "حلقه‌ها در پایتون: for با range() و روی لیست، while با شرط پایان، break و continue. "
                    "تمرین‌ها: جمع اعداد ۱ تا ۱۰۰، جدول ضرب، و حدس عدد با while."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: range(1, 10) عدد ۱۰ را شامل نمی‌شود؛ و حلقهٔ while بی‌پایان.",
            },
            {
                "title": "تابع‌ها",
                "objectives": "تعریف تابع با def\nپارامتر و مقدار بازگشتی (return)\nتفاوت print و return",
                "brief": (
                    "تابع در پایتون: تعریف با def، پارامترها، مقدار پیش‌فرض، return و تفاوتش با print. "
                    "تمرین: تابع محاسبهٔ میانگین یک لیست و تابع تشخیص عدد زوج."
                ),
                "teaching_notes": FA_TUTOR + " بیشتر مبتدی‌ها print و return را قاطی می‌کنند؛ با یک مثال کنار هم نشانشان بده.",
            },
        ],
        "quizzes": [
            {
                "title": "آزمون متغیرها و شرط‌ها",
                "lesson": 2,
                "questions": [
                    mcq("نوع مقدار 3.5 در پایتون چیست؟", ["int", "float", "str", "bool"], "B",
                        "عددهای اعشاری از نوع float هستند.", "انواع داده"),
                    mcq("حاصل اجرای '2' + 2 چیست؟", ["4", "22", "خطای TypeError", "'2 2'"], "C",
                        "رشته و عدد را نمی‌شود با + جمع کرد؛ اول یکی را تبدیل کنید.", "تبدیل نوع"),
                    mcq("برای مقایسهٔ برابری دو مقدار از کدام عملگر استفاده می‌شود؟", ["=", "==", "===", ":="], "B",
                        "= برای مقداردهی است و == برای مقایسه.", "عملگر مقایسه"),
                    short("کدام تابع داخلی پایتون نوع یک مقدار را نشان می‌دهد؟", "type", ["type()", "type(x)"],
                          "type(x) نوع x را برمی‌گرداند.", "type()"),
                ],
            },
            {
                "title": "آزمون حلقه‌ها و تابع‌ها (با هوش مصنوعی)",
                "lesson": 4,
                "mode": Quiz.AI,
                "count": 6,
                "prompt": (
                    "۶ سؤال به فارسی دربارهٔ حلقه‌های for/while و تابع‌ها در پایتون برای مبتدی. ترکیبی از چندگزینه‌ای و "
                    "«خروجی این کد چیست؟» با قطعه‌کدهای کوتاه. حداقل یک سؤال دربارهٔ range() و یک سؤال دربارهٔ "
                    "تفاوت print و return باشد."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Algebra
    {
        "title": "ریاضی دبیرستان: جبر",
        "description": (
            "جبر پایهٔ دبیرستان قدم به قدم: عبارت‌های جبری، معادلهٔ درجه اول، اتحادها و تجزیه، و معادلهٔ درجه دوم. "
            "با تمرین حل‌شده و تمرین‌هایی که هوش مصنوعی یکی‌یکی از شما می‌پرسد."
        ),
        "lessons": [
            {
                "title": "عبارت‌های جبری و ساده کردن",
                "objectives": "شناخت جملهٔ متشابه\nجمع و تفریق عبارت‌های جبری\nضرب یک جمله در یک عبارت (پخش کردن)",
                "brief": (
                    "پایهٔ دهم: عبارت جبری، ضریب و متغیر، جمله‌های متشابه، ساده کردن و خاصیت پخشی. "
                    "۵ مثال حل‌شده و ۶ تمرین از آسان به سخت، مثل 3x + 2(x - 4)."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: علامت منفی پشت پرانتز را به همهٔ جمله‌ها پخش نمی‌کنند.",
            },
            {
                "title": "معادلهٔ درجه اول",
                "objectives": "حل معادلهٔ یک‌مجهولی درجه اول\nانتقال جمله‌ها به دو طرف تساوی\nحل مسئلهٔ کلامی با معادله",
                "brief": (
                    "حل معادلهٔ درجه اول با یک مجهول (مثل 2x + 3 = 11 و معادله‌های کسری ساده) و تبدیل مسئلهٔ کلامی "
                    "به معادله (سن، قیمت، مسافت). بعد از هر جواب، درستی را با جای‌گذاری چک کن."
                ),
                "teaching_notes": FA_TUTOR + " از دانش‌آموز بخواه همیشه جواب را در معادله جای‌گذاری کند و چک کند.",
            },
            {
                "title": "اتحادها و تجزیه",
                "objectives": "اتحاد مربع دوجمله‌ای و مزدوج\nفاکتورگیری از عامل مشترک\nتجزیهٔ سه‌جمله‌ای ساده",
                "brief": (
                    "اتحادهای (a+b)²، (a-b)² و (a+b)(a-b)، فاکتورگیری و تجزیهٔ x² + bx + c. "
                    "اول هر اتحاد را با مساحت مربع شهودی توضیح بده، بعد تمرین."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: (a+b)² = a² + b². جملهٔ 2ab را با شکل نشان بده.",
            },
            {
                "title": "معادلهٔ درجه دوم",
                "objectives": "حل با تجزیه\nحل با فرمول کلی (دلتا)\nتشخیص تعداد ریشه‌ها از روی دلتا",
                "brief": (
                    "معادلهٔ درجه دوم ax² + bx + c = 0: حل با تجزیه، روش مربع کامل و فرمول دلتا (Δ = b² - 4ac). "
                    "تفسیر Δ > 0، Δ = 0 و Δ < 0. شش تمرین با عددهای ساده."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: علامت b در فرمول (-b) و فراموش کردن ± .",
            },
        ],
        "quizzes": [
            {
                "title": "آزمون معادله و اتحادها",
                "lesson": 3,
                "questions": [
                    short("معادلهٔ 2x + 3 = 11 را حل کنید. x چند است؟", "4", ["۴", "x=4", "x = 4", "x=۴"],
                          "2x = 8 پس x = 4.", "معادلهٔ درجه اول"),
                    mcq("حاصل (a + b)² کدام است؟", ["a² + b²", "a² + 2ab + b²", "a² - 2ab + b²", "2a + 2b"], "B",
                        "(a+b)(a+b) = a² + ab + ab + b².", "اتحاد مربع دوجمله‌ای"),
                    mcq("تجزیهٔ x² - 9 کدام است؟", ["(x - 3)²", "(x + 9)(x - 1)", "(x - 3)(x + 3)", "(x - 9)(x + 1)"], "C",
                        "اتحاد مزدوج: a² - b² = (a - b)(a + b).", "اتحاد مزدوج"),
                    short("ساده‌شدهٔ 3x + 2(x - 4) چیست؟", "5x - 8", ["5x-8", "۵x - ۸", "۵x-۸"],
                          "3x + 2x - 8 = 5x - 8.", "ساده کردن عبارت"),
                ],
            },
            {
                "title": "تمرین معادلهٔ درجه دوم (با هوش مصنوعی)",
                "lesson": 4,
                "mode": Quiz.AI,
                "count": 5,
                "prompt": (
                    "۵ معادلهٔ درجه دوم به فارسی، از آسان به سخت: دو تا با تجزیه، دو تا با فرمول دلتا، و یکی که ریشهٔ "
                    "حقیقی ندارد. دانش‌آموز ریشه‌ها را بنویسد. ضریب‌ها عدد صحیح کوچک باشند."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Interview
    {
        "title": "آمادگی برای مصاحبهٔ شغلی",
        "description": (
            "تمرین مصاحبهٔ شغلی با هوش مصنوعی به‌عنوان مصاحبه‌گر: معرفی خود، پاسخ به سؤال‌های رفتاری با روش STAR، "
            "مصاحبهٔ شبیه‌سازی‌شده برای شغل خودتان و مذاکرهٔ حقوق."
        ),
        "lessons": [
            {
                "title": "معرفی خود در یک دقیقه",
                "objectives": "ساختن پاسخ «از خودتان بگویید» در سه بخش\nوصل کردن تجربه‌ها به شغل مورد نظر\nکوتاه و روشن صحبت کردن",
                "brief": (
                    "پاسخ به سؤال «کمی از خودتان بگویید» با ساختار حال-گذشته-آینده در حدود یک دقیقه. "
                    "اول شغل و سابقهٔ دانش‌آموز را بپرس، یک نمونه بنویس، بعد او پاسخ خودش را بدهد و بازخورد بگیرد."
                ),
                "teaching_notes": FA_TUTOR + " اگر اپ صدا دارد، بخواه پاسخ را با صدا بدهد. بازخورد: یک نقطهٔ قوت و حداکثر دو پیشنهاد.",
            },
            {
                "title": "سؤال‌های رفتاری با روش STAR",
                "objectives": "شناخت چهار بخش STAR\nآماده کردن ۳ داستان از تجربه‌های واقعی\nبیان نتیجه با عدد و شاهد",
                "brief": (
                    "روش STAR (موقعیت، وظیفه، اقدام، نتیجه) برای سؤال‌هایی مثل «از زمانی بگو که با همکار اختلاف داشتی». "
                    "یک مثال کامل، بعد سه سؤال رفتاری رایج یکی‌یکی و بازخورد روی هر بخش STAR."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: بخش «اقدام» با «ما» گفته می‌شود نه «من»، و «نتیجه» جا می‌افتد.",
            },
            {
                "title": "مصاحبهٔ شبیه‌سازی‌شده",
                "objectives": "تجربهٔ یک مصاحبهٔ کامل برای شغل خودتان\nپاسخ به سؤال‌های فنی و رفتاری زیر فشار زمان\nپرسیدن سؤال از مصاحبه‌گر",
                "brief": (
                    "یک مصاحبهٔ شبیه‌سازی‌شدهٔ ۸ سؤالی. اول عنوان شغل و سطح (کارآموز، کارشناس، ارشد) را بپرس، "
                    "بعد نقش مصاحبه‌گر را بازی کن: سؤال‌ها را یکی‌یکی بپرس و وسط کار بازخورد نده. در پایان گزارش کامل بده."
                ),
                "teaching_notes": (
                    FA_TUTOR + " در نقش بمان و سؤال‌های پیگیری بپرس. بعد از مصاحبه: سه نقطهٔ قوت، سه مورد برای بهتر شدن، "
                    "و یک پاسخ نمونهٔ بهتر برای ضعیف‌ترین جواب."
                ),
            },
            {
                "title": "مذاکرهٔ حقوق و مزایا",
                "objectives": "تحقیق دربارهٔ حقوق بازار\nبیان عدد مورد نظر با دلیل\nمذاکره روی مزایا به جز حقوق",
                "brief": (
                    "مذاکرهٔ حقوق بعد از پیشنهاد شغلی: چطور عدد بازار را پیدا کنیم، چه زمانی عدد بگوییم، "
                    "و جمله‌های مؤدبانه برای درخواست بیشتر. در پایان یک نقش‌آفرینی کوتاه با مدیر منابع انسانی."
                ),
                "teaching_notes": FA_TUTOR + " تمرین را واقع‌بینانه نگه دار؛ مدیر منابع انسانی گاهی «نه» می‌گوید.",
            },
        ],
        "quizzes": [
            {
                "title": "آزمون روش STAR",
                "lesson": 2,
                "questions": [
                    mcq("حرف R در روش STAR یعنی چه؟", ["Reason (دلیل)", "Result (نتیجه)", "Role (نقش)", "Review (مرور)"], "B",
                        "STAR = Situation, Task, Action, Result.", "روش STAR"),
                    mcq("کدام بخش STAR باید بیشترین زمان پاسخ را بگیرد؟",
                        ["موقعیت", "وظیفه", "اقدام", "نتیجه"], "C",
                        "مصاحبه‌گر می‌خواهد بداند شما چه کردید؛ اقدام قلب پاسخ است.", "روش STAR"),
                    mcq("بهترین پاسخ به «بزرگ‌ترین نقطه‌ضعفت چیست؟» کدام است؟",
                        ["من هیچ نقطه‌ضعفی ندارم.", "من بیش از حد کمال‌گرا هستم.",
                         "یک ضعف واقعی که روی آن کار می‌کنم و قدمی که برداشته‌ام.", "از جواب دادن طفره بروم."], "C",
                        "صداقت به همراه برنامهٔ بهبود، اعتماد می‌سازد.", "سؤال‌های رایج"),
                ],
            },
            {
                "title": "تمرین سؤال‌های رفتاری (با هوش مصنوعی)",
                "lesson": 2,
                "mode": Quiz.AI,
                "count": 4,
                "prompt": (
                    "۴ سؤال مصاحبهٔ رفتاری به فارسی متناسب با شغلی که دانش‌آموز گفته (مثل کار تیمی، شکست، فشار زمانی، "
                    "رهبری). دانش‌آموز با روش STAR جواب کوتاه بنویسد. هر پاسخ را بر اساس کامل بودن چهار بخش STAR و "
                    "داشتن نتیجهٔ مشخص بسنج."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Finance
    {
        "title": "سواد مالی شخصی",
        "description": (
            "مدیریت پول برای همه: بودجه‌بندی، صندوق اضطراری، تورم، سود مرکب و پس‌انداز، و بدهی. "
            "با مثال‌هایی به تومان و تمرین روی درآمد و هزینهٔ خودتان. این کلاس آموزشی است و توصیهٔ سرمایه‌گذاری نیست."
        ),
        "lessons": [
            {
                "title": "بودجه‌بندی ماهانه",
                "objectives": "ثبت درآمد و هزینه‌ها\nقاعدهٔ ۵۰/۳۰/۲۰\nتفاوت هزینهٔ ضروری و اختیاری",
                "brief": (
                    "بودجه‌بندی ماهانه با قاعدهٔ ۵۰/۳۰/۲۰ (ضروری/خواسته‌ها/پس‌انداز). یک مثال با حقوق ۲۰ میلیون تومان، "
                    "بعد کمک کن دانش‌آموز بودجهٔ خودش را با عددهای تقریبی بچیند (لازم نیست عدد واقعی بگوید)."
                ),
                "teaching_notes": FA_TUTOR + " دربارهٔ اطلاعات مالی شخصی کنجکاوی نکن؛ عدد تقریبی یا فرضی کافی است.",
            },
            {
                "title": "صندوق اضطراری",
                "objectives": "چرا صندوق اضطراری لازم است\nچند ماه هزینه کافی است\nکجا نگهش داریم",
                "brief": (
                    "صندوق اضطراری: معادل ۳ تا ۶ ماه هزینهٔ ضروری، جدا از پس‌انداز بلندمدت، در جایی که سریع در دسترس باشد. "
                    "یک برنامهٔ ساده برای ساختنش در ۱۲ ماه."
                ),
                "teaching_notes": FA_TUTOR,
            },
            {
                "title": "تورم و ارزش پول",
                "objectives": "تورم چیست\nتفاوت بازده اسمی و واقعی\nاثر تورم بر پس‌انداز نقدی",
                "brief": (
                    "تورم و کاهش قدرت خرید با مثال قیمت نان و اجاره در چند سال. بازده واقعی ≈ بازده اسمی منهای تورم. "
                    "چرا نگه داشتن پول نقد در تورم بالا ارزشش را کم می‌کند."
                ),
                "teaching_notes": FA_TUTOR + " سیاسی یا پیش‌بینی بازار نکن؛ فقط مفهوم را آموزش بده.",
            },
            {
                "title": "سود مرکب و پس‌انداز بلندمدت",
                "objectives": "تفاوت سود ساده و مرکب\nمحاسبهٔ سود مرکب برای چند سال\nاهمیت زود شروع کردن",
                "brief": (
                    "سود مرکب: فرمول A = P(1 + r)ⁿ با مثال ۱۰ میلیون تومان با سود سالانهٔ ۲۰٪ در ۲، ۵ و ۱۰ سال. "
                    "مقایسه با سود ساده و تمرین محاسبه با ماشین‌حساب."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: سود را هر سال فقط روی اصل پول حساب می‌کنند.",
            },
            {
                "title": "بدهی، وام و اقساط",
                "objectives": "هزینهٔ واقعی وام\nبدهی خوب و بد\nروش‌های بازپرداخت (گلولهٔ برفی و بهمن)",
                "brief": (
                    "وام و بدهی: نرخ سود، کارمزد و هزینهٔ کل وام؛ چه زمانی وام گرفتن منطقی است؛ "
                    "روش گلولهٔ برفی (کوچک‌ترین بدهی اول) و بهمن (بیشترین نرخ اول) با یک مثال."
                ),
                "teaching_notes": FA_TUTOR,
            },
        ],
        "quizzes": [
            {
                "title": "آزمون بودجه و سود مرکب",
                "lesson": 4,
                "questions": [
                    mcq("در قاعدهٔ ۵۰/۳۰/۲۰، عدد ۲۰ مربوط به چیست؟", ["هزینه‌های ضروری", "خواسته‌ها و تفریح", "پس‌انداز و بازپرداخت بدهی", "مالیات"], "C",
                        "۵۰٪ ضروری، ۳۰٪ خواسته‌ها، ۲۰٪ پس‌انداز.", "بودجه‌بندی"),
                    mcq("صندوق اضطراری معمولاً معادل چند ماه هزینهٔ ضروری پیشنهاد می‌شود؟", ["نیم ماه", "۳ تا ۶ ماه", "۲ سال", "۱۰ سال"], "B",
                        "۳ تا ۶ ماه برای بیشتر خانواده‌ها کافی است.", "صندوق اضطراری"),
                    short("۱۰ میلیون تومان با سود مرکب سالانهٔ ۲۰٪، بعد از ۲ سال چند میلیون تومان می‌شود؟", "14.4",
                          ["14.4 میلیون", "۱۴.۴", "۱۴٫۴", "۱۴٫۴ میلیون", "14400000", "14,400,000"],
                          "10 × 1.2 × 1.2 = 14.4 میلیون تومان.", "سود مرکب"),
                    mcq("اگر سود سپرده ۲۵٪ و تورم ۳۵٪ باشد، بازده واقعی تقریباً چقدر است؟", ["۶۰٪", "۱۰٪", "منفی ۱۰٪", "صفر"], "C",
                        "بازده واقعی ≈ ۲۵ - ۳۵ = منفی ۱۰٪؛ قدرت خرید کم می‌شود.", "بازده واقعی"),
                ],
            },
            {
                "title": "تمرین تصمیم‌های مالی (با هوش مصنوعی)",
                "lesson": 5,
                "mode": Quiz.AI,
                "count": 5,
                "prompt": (
                    "۵ سناریوی کوتاه به فارسی از زندگی روزمره (خرید قسطی گوشی، کارت اعتباری، وام خودرو، دو بدهی با "
                    "نرخ متفاوت، خرج غیرمنتظره). دانش‌آموز تصمیم بگیرد و دلیلش را بگوید. ارزیابی بر اساس مفاهیم بودجه، "
                    "صندوق اضطراری و هزینهٔ واقعی وام؛ بدون توصیهٔ سرمایه‌گذاری خاص."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Business email
    {
        "title": "Business Email Writing (Persian → English)",
        "description": (
            "نوشتن ایمیل کاری حرفه‌ای به انگلیسی برای فارسی‌زبان‌ها: ساختار ایمیل رسمی، عبارت‌های پرکاربرد، "
            "ترجمهٔ جمله‌های کاری از فارسی، پیگیری و درخواست مؤدبانه، و پاسخ به شکایت. سطح B1 به بالا."
        ),
        "lessons": [
            {
                "title": "Useful phrases for business emails",
                "kind": "vocabulary",
                "objectives": (
                    "Open and close an email at the right level of formality\n"
                    "Use 20 common phrases (I am writing to…, Please find attached…, I look forward to…)"
                ),
                "brief": (
                    "B1-B2: 20 key phrases for business emails in four groups: openings (Dear Ms Smith, I hope you are "
                    "well), reasons for writing (I am writing to enquire about…), attachments and requests (Please find "
                    "attached…, Could you please…), and closings (I look forward to hearing from you, Best regards)."
                ),
                "teaching_notes": PERSIAN + " Point out formal vs informal pairs (Hi/Dear, Thanks/Thank you for…).",
            },
            {
                "title": "Structure of a formal email",
                "kind": "writing",
                "objectives": (
                    "Write a clear subject line\n"
                    "Organise an email: greeting, purpose, details, action, closing\n"
                    "Keep it short and polite"
                ),
                "brief": (
                    "B1-B2: the structure of a formal email: subject line, greeting, purpose in the first sentence, "
                    "details in short paragraphs, a clear call to action, closing and signature. Task: a 120-word email "
                    "to a supplier asking for a price quote."
                ),
                "teaching_notes": PERSIAN + " Persian business emails often open with long greetings; show the shorter English style.",
            },
            {
                "title": "Translating work emails from Persian",
                "kind": "translation",
                "objectives": (
                    "Translate common Persian work sentences into natural English\n"
                    "Avoid word-for-word translation (e.g. «خسته نباشید», «با سلام و احترام»)"
                ),
                "brief": (
                    "B1-B2: Persian-to-English translation of real work-email sentences: requests, meeting times, "
                    "delays, thanks and apologies (e.g. «لطفاً فایل پیوست را بررسی بفرمایید», «جلسه به هفتهٔ بعد موکول شد»). "
                    "Focus on polite modals (could, would), the passive and natural set phrases."
                ),
                "teaching_notes": PERSIAN + " Explain when a Persian phrase has no direct English equivalent and what natives write instead.",
            },
            {
                "title": "Following up and making polite requests",
                "kind": "writing",
                "objectives": (
                    "Write a follow-up email without sounding rude\n"
                    "Soften requests (I was wondering if…, Would it be possible to…)"
                ),
                "brief": (
                    "B2: follow-up emails and polite requests. Compare direct and softened versions "
                    "(Send me the report. → Could you send me the report by Friday?). Task: a 100-word follow-up to a "
                    "client who has not replied for a week."
                ),
                "teaching_notes": PERSIAN,
            },
            {
                "title": "Replying to a complaint",
                "kind": "writing",
                "objectives": (
                    "Apologise professionally\n"
                    "Explain what happened and offer a solution\n"
                    "Keep a calm, positive tone"
                ),
                "brief": (
                    "B2: replying to a customer complaint about a late delivery: thank, apologise, explain briefly, "
                    "offer a solution and close positively. Model email first, then the student writes 150 words."
                ),
                "teaching_notes": PERSIAN + " Watch for over-apologising and for blaming the customer.",
            },
        ],
        "quizzes": [
            {
                "title": "Email phrases quiz",
                "lesson": 1,
                "questions": [
                    mcq("Which closing is best for a formal email to a new client?",
                        ["Cheers", "Best regards", "See ya", "Love"], "B",
                        "«Best regards» is polite and professional.", "closings"),
                    short("Complete: \"I look forward to ___ from you.\"", "hearing", ["hearing back"],
                          "After «look forward to» we use the -ing form.", "look forward to + -ing"),
                    mcq("Which sentence is the most polite request?",
                        ["Send me the file now.", "I want the file.",
                         "Could you please send me the file?", "You must send the file."], "C",
                        "«Could you please…» softens the request.", "polite requests"),
                    mcq("A natural English translation of «فایل پیوست را ملاحظه فرمایید» is:",
                        ["Please see the attached file.", "Please observe the file in the attachment.",
                         "Look at the attach file.", "The file is attached, notice it."], "A",
                        "«Please see the attached file» or «Please find attached…» are the set phrases.", "attachments"),
                ],
            },
            {
                "title": "Email writing check (AI)",
                "lesson": 5,
                "mode": Quiz.AI,
                "count": 5,
                "prompt": (
                    "5 short tasks, B1-B2 level, for Persian speakers writing business emails in English: two "
                    "Persian sentences to translate into a formal email sentence, one rude sentence to rewrite "
                    "politely, one subject line to write for a given situation, and one complaint reply opening. "
                    "Accept any natural, correct answer; explain the main error briefly."
                ),
            },
        ],
    },
    # ------------------------------------------------------------------ Biology exam
    {
        "title": "آمادگی کنکور زیست‌شناسی",
        "description": (
            "مرور مفهومی و تست‌محور زیست‌شناسی دبیرستان برای کنکور: سلول، تقسیم سلولی، ژنتیک و گوارش. "
            "هوش مصنوعی مفهوم را توضیح می‌دهد، تست می‌پرسد و دام‌های رایج تست‌ها را نشان می‌دهد."
        ),
        "lessons": [
            {
                "title": "سلول و اندامک‌ها",
                "objectives": "کار هر اندامک اصلی\nتفاوت سلول گیاهی و جانوری\nتفاوت پروکاریوت و یوکاریوت",
                "brief": (
                    "مرور سلول برای کنکور: غشا، هسته، میتوکندری، ریبوزوم، شبکهٔ آندوپلاسمی، دستگاه گلژی، لیزوزوم، "
                    "کلروپلاست و دیواره. جدول مقایسهٔ سلول گیاهی و جانوری و ۶ تست مفهومی."
                ),
                "teaching_notes": FA_TUTOR + " بعد از هر تست، گزینه‌های غلط را هم توضیح بده؛ کنکور روی جزئیات دام می‌گذارد.",
            },
            {
                "title": "تقسیم سلولی: میتوز و میوز",
                "objectives": "مراحل میتوز\nتفاوت میتوز و میوز\nتعداد کروموزوم در هر مرحله",
                "brief": (
                    "میتوز و میوز: مراحل (پروفاز، متافاز، آنافاز، تلوفاز)، رفتار کروموزوم‌ها، کراسینگ‌اوور، "
                    "و تعداد کروموزوم و کروماتید در هر مرحله برای سلول ۲n = 46. ۸ تست از آسان به سخت."
                ),
                "teaching_notes": FA_TUTOR + " اشتباه رایج: شمردن کروماتید به جای کروموزوم بعد از همانندسازی.",
            },
            {
                "title": "ژنتیک مندلی",
                "objectives": "ژنوتیپ و فنوتیپ\nحل مسئلهٔ تک‌صفتی با مربع پانت\nغالب ناقص و هم‌توانی",
                "brief": (
                    "ژنتیک مندلی: ال، ژنوتیپ، فنوتیپ، آمیزش تک‌صفتی با مربع پانت (Aa × Aa)، آمیزش آزمون، غالب ناقص، "
                    "هم‌توانی و گروه‌های خونی ABO. ۶ مسئلهٔ کنکوری."
                ),
                "teaching_notes": FA_TUTOR + " از دانش‌آموز بخواه برای هر مسئله مربع پانت را خودش بکشد.",
            },
            {
                "title": "دستگاه گوارش",
                "objectives": "مسیر غذا و کار هر بخش\nآنزیم‌های گوارشی و محل اثرشان\nجذب در روده باریک",
                "brief": (
                    "گوارش در انسان: دهان، معده، رودهٔ باریک و بزرگ، کبد و پانکراس؛ آنزیم‌ها (آمیلاز، پپسین، لیپاز، "
                    "تریپسین) و محل اثرشان؛ پرزها و جذب. ۶ تست مفهومی."
                ),
                "teaching_notes": FA_TUTOR,
            },
        ],
        "quizzes": [
            {
                "title": "آزمون سلول و ژنتیک",
                "lesson": 3,
                "questions": [
                    mcq("محل اصلی تنفس سلولی هوازی و تولید ATP کدام اندامک است؟", ["ریبوزوم", "میتوکندری", "دستگاه گلژی", "لیزوزوم"], "B",
                        "میتوکندری نیروگاه سلول است.", "اندامک‌ها"),
                    mcq("حاصل میوز در یک سلول ۲n کدام است؟",
                        ["دو سلول ۲n", "چهار سلول n", "دو سلول n", "چهار سلول ۲n"], "B",
                        "میوز دو تقسیم پشت سر هم دارد و چهار سلول هاپلوئید می‌سازد.", "میوز"),
                    mcq("در آمیزش Aa × Aa با غالبیت کامل، نسبت فنوتیپی فرزندان چیست؟", ["۱:۱", "۱:۲:۱", "۳:۱", "همه یکسان"], "C",
                        "ژنوتیپ‌ها ۱AA : ۲Aa : ۱aa هستند و فنوتیپ ۳ غالب به ۱ مغلوب.", "ژنتیک مندلی"),
                    short("آنزیم پپسین در کدام بخش دستگاه گوارش فعال است؟", "معده", ["در معده", "stomach"],
                          "پپسین در محیط اسیدی معده پروتئین‌ها را تجزیه می‌کند.", "آنزیم‌های گوارشی"),
                ],
            },
            {
                "title": "تست کنکوری تقسیم سلولی (با هوش مصنوعی)",
                "lesson": 2,
                "mode": Quiz.AI,
                "count": 8,
                "prompt": (
                    "۸ تست چهارگزینه‌ای به سبک کنکور سراسری ایران دربارهٔ میتوز و میوز: مراحل، تعداد کروموزوم و "
                    "کروماتید، کراسینگ‌اوور و تفاوت دو تقسیم. حداقل دو تست ترکیبی و دشوار. بعد از هر جواب، "
                    "دلیل نادرستی گزینه‌های دیگر را کوتاه بگو."
                ),
            },
        ],
    },
]


CLASSES += ENGLISH_CLASSES


class Command(BaseCommand):
    help = "Create sample classes (programming, math, interview prep, finance, biology and several English classes) on a demo instructor."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="demo", help="Instructor user (created if missing).")
        parser.add_argument("--password", default=os.environ.get("DEMO_INSTRUCTOR_PASSWORD", "demo-pass-123"))
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, username, password, dry_run=False, **options):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username, defaults={"email": f"{username}@example.com", "is_staff": True}
        )
        if created:
            user.set_password(password)
            user.save()
        user.groups.add(ensure_instructors_group())
        instructor, _ = Instructor.objects.get_or_create(user=user, defaults={"display_name": "Demo Instructor"})

        totals = {"classes": 0, "lessons": 0, "quizzes": 0, "questions": 0}
        for spec in CLASSES:
            course, new = Course.objects.get_or_create(
                instructor=instructor, title=spec["title"], defaults={"description": spec["description"], "listed": True}
            )
            totals["classes"] += new

            lessons: list[Lesson] = []
            for order, data in enumerate(spec["lessons"], start=1):
                lesson = course.lessons.filter(title=data["title"]).first()
                if lesson is None:
                    lesson = Lesson(course=course, order=order, kind=data.get("kind", "general"),
                                    **{k: data[k] for k in ("title", "objectives", "brief", "teaching_notes")})
                    lesson.full_clean()
                    lesson.save()
                    totals["lessons"] += 1
                lessons.append(lesson)

            for qspec in spec["quizzes"]:
                if course.quizzes.filter(title=qspec["title"]).exists():
                    continue
                mode = qspec.get("mode", Quiz.MANUAL)
                quiz = Quiz(
                    course=course,
                    lesson=lessons[qspec["lesson"] - 1],
                    title=qspec["title"],
                    mode=mode,
                    prompt=qspec.get("prompt", ""),
                    ai_question_count=qspec.get("count", 5),
                )
                quiz.full_clean()
                quiz.save()
                totals["quizzes"] += 1
                for n, q in enumerate(qspec.get("questions", []), start=1):
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
                    totals["questions"] += 1

            self.stdout.write(f"  {course.join_code}  {course.title}")

        if dry_run:
            transaction.set_rollback(True)
        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry run] ' if dry_run else ''}Created {totals['classes']} classes, {totals['lessons']} lessons, "
                f"{totals['quizzes']} quizzes, {totals['questions']} questions for '{username}'."
            )
        )
