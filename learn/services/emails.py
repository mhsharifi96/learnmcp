"""Transactional emails (verification, inactivity reminders), in the student's language."""

import logging
from html import escape

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

log = logging.getLogger(__name__)

TEXTS = {
    "verify": {
        "fa": {
            "subject": "تأیید ایمیل در learnmcp",
            "body": (
                "سلام {name}،\n\n"
                "برای تأیید ایمیل و فعال شدن حساب learnmcp روی لینک زیر بزنید:\n\n{link}\n\n"
                "این لینک تا {days} روز معتبر است. اگر شما ثبت‌نام نکرده‌اید، این ایمیل را نادیده بگیرید."
            ),
            "button": "تأیید ایمیل",
        },
        "en": {
            "subject": "Confirm your email for learnmcp",
            "body": (
                "Hi {name},\n\n"
                "Confirm your email to activate your learnmcp account:\n\n{link}\n\n"
                "This link works for {days} days. If you didn't sign up, ignore this email."
            ),
            "button": "Confirm email",
        },
    },
    "reminder": {
        "fa": {
            "subject": "{days} روز است که «{course}» را مرور نکرده‌اید",
            "body": (
                "سلام {name}،\n\n"
                "{days} روز است که درس‌های کلاس «{course}» ({instructor}) را مرور نکرده‌اید.\n"
                "اپ هوش مصنوعی خود (Claude یا ChatGPT) را باز کنید و بنویسید: «درس‌هایم را ادامه بده».\n\n"
                "کلاس‌های من: {link}\n\n"
                "برای خاموش کردن این یادآورها، در صفحهٔ «کلاس‌های من» گزینهٔ یادآور ایمیلی را خاموش کنید."
            ),
            "button": "کلاس‌های من",
        },
        "en": {
            "subject": "You haven't studied “{course}” for {days} days",
            "body": (
                "Hi {name},\n\n"
                "You haven't reviewed the lessons of “{course}” ({instructor}) for {days} days.\n"
                "Open your AI app (Claude or ChatGPT) and say: “continue my lessons”.\n\n"
                "My classes: {link}\n\n"
                "To stop these reminders, turn off email reminders on the “My classes” page."
            ),
            "button": "My classes",
        },
    },
}


def _render(kind: str, lang: str, **ctx) -> tuple[str, str, str]:
    lang = lang if lang in ("fa", "en") else "fa"
    t = TEXTS[kind][lang]
    subject = t["subject"].format(**ctx)
    text = t["body"].format(**ctx)
    direction = "rtl" if lang == "fa" else "ltr"
    paragraphs = "".join(
        f"<p style='margin:0 0 14px'>{escape(p).replace(chr(10), '<br>')}</p>"
        for p in text.split("\n\n")
        if p.strip() and p.strip() != ctx.get("link")
    )
    link = ctx.get("link")
    button = (
        f"<p style='margin:20px 0'><a href='{escape(link)}' style='background:#1d4e89;color:#fff;"
        f"padding:10px 18px;border-radius:8px;text-decoration:none'>{escape(t['button'])}</a></p>"
        f"<p style='font-size:12px;color:#666;direction:ltr'>{escape(link)}</p>"
        if link
        else ""
    )
    html = (
        f"<div dir='{direction}' style='font-family:Tahoma,Arial,sans-serif;font-size:15px;line-height:1.8;"
        f"color:#1b1b1b;max-width:560px'>{paragraphs}{button}</div>"
    )
    return subject, text, html


def send(kind: str, to: str, lang: str, **ctx) -> bool:
    subject, text, html = _render(kind, lang, **ctx)
    msg = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [to])
    msg.attach_alternative(html, "text/html")
    try:
        msg.send()
    except Exception:  # SMTP down or misconfigured: log, never crash the request.
        log.exception("Sending %s email to %s failed", kind, to)
        return False
    return True
