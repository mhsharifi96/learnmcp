"""255 free public courses (Persian, high-search titles) used to fill the class catalog.

Each part holds 50 courses: {category, title, hook, outcomes, audience, lessons}.
Only the description and the lesson titles are public; lesson content and quizzes stay empty
until the site admin fills them, and students need the admin's approval to get access.
"""

from .part1 import COURSES as _P1
from .part2 import COURSES as _P2
from .part3 import COURSES as _P3
from .part4 import COURSES as _P4
from .part5 import COURSES as _P5

COURSES = [*_P1, *_P2, *_P3, *_P4, *_P5]

CATEGORY_NOTES = {
    "language": "تمرین‌ها روی موقعیت‌های واقعی ساخته شده‌اند تا آنچه یاد می‌گیرید را همان روز در مکالمه و نوشتن به کار ببرید.",
    "code": "هر درس با مثال‌های عملی و پروژه‌های کوچک همراه است تا مفاهیم را با نوشتن کد واقعی تثبیت کنید.",
    "office": "همهٔ مثال‌ها از کارهای روزمرهٔ اداری و فایل‌های واقعی گرفته شده تا مهارت‌ها را مستقیم سر کار استفاده کنید.",
    "design": "پروژه‌محور پیش می‌روید و در پایان دوره چند نمونه‌کار آماده برای پورتفولیوی خود دارید.",
    "marketing": "روی کسب‌وکارهای واقعی تمرین می‌کنید و با چک‌لیست‌های آماده، هر مرحله را روی پیج یا سایت خودتان اجرا می‌کنید.",
    "academic": "مفاهیم از پایه و با حل تمرین‌های طبقه‌بندی‌شده جلو می‌روند تا برای امتحان و آزمون آماده شوید.",
    "finance": "محتوا آموزشی است و توصیهٔ سرمایه‌گذاری نیست؛ هدف این است که با مفاهیم و ابزارها آشنا شوید و تصمیم آگاهانه بگیرید.",
    "career": "با تمرین‌های عملی و نمونه‌های واقعی، قدم‌به‌قدم برای بازار کار و رشد شغلی آماده می‌شوید.",
    "ai": "هر درس با تمرین روی ابزارهای واقعی هوش مصنوعی همراه است و نسخهٔ رایگان این ابزارها برای همهٔ تمرین‌ها کافی است.",
    "engineering": "مفاهیم با پروژه‌های صنعتی و درسی واقعی تمرین می‌شوند تا مهارت را مستقیم در دانشگاه و محل کار به کار ببرید.",
    "hobby": "هر جلسه یک تمرین عملی کوتاه دارد؛ نتیجهٔ کارتان را برای هوش مصنوعی توضیح می‌دهید یا عکسش را می‌فرستید و بازخورد می‌گیرید.",
    "skills": "تمرین‌های کوتاه روزانه کمک می‌کند مهارت‌ها را به عادت تبدیل کنید و نتیجه را در زندگی روزمره ببینید.",
}

HOW_IT_WORKS = (
    "روش یادگیری: درس‌ها را با هوش مصنوعی خودتان (ChatGPT، Gemini، Claude یا DeepSeek، حتی نسخهٔ رایگان) "
    "قدم‌به‌قدم می‌خوانید، تمرین می‌کنید و آزمون می‌دهید؛ هر جا گیر کنید مدرس باخبر می‌شود و کمکتان می‌کند. "
    "ثبت‌نام در این دوره رایگان است و بعد از تأیید، همهٔ درس‌ها و آزمون‌ها برایتان باز می‌شود."
)


def description(c: dict) -> str:
    outcomes = "\n".join(f"• {o}" for o in c["outcomes"])
    parts = [
        c["hook"].strip(),
        f"در این دورهٔ رایگان یاد می‌گیرید:\n{outcomes}",
        f"این دوره مناسب چه کسانی است؟ {c['audience'].strip()}",
        CATEGORY_NOTES.get(c.get("category", ""), ""),
        HOW_IT_WORKS,
    ]
    return "\n\n".join(p for p in parts if p)
