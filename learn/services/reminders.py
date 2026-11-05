"""Inactivity reminder emails: instructors set N days per class; students who haven't studied get an email."""

from datetime import timedelta

from django.conf import settings
from django.db.models import Max
from django.utils import timezone

from learn.models import Course, Enrollment
from learn.services import emails


def last_seen(enrollment):
    return max(filter(None, [enrollment.last_activity_at, getattr(enrollment, "last_event", None), enrollment.joined_at]))


def due(now=None):
    """Yield (enrollment, inactive_days) for every reminder that should go out now.

    A student is reminded once N days pass without activity, then again every N days while still inactive.
    Only verified emails that haven't opted out are used.
    """
    now = now or timezone.now()
    for course in Course.objects.filter(reminder_after_days__gt=0).select_related("instructor"):
        every = timedelta(days=course.reminder_after_days)
        qs = (
            Enrollment.objects.filter(
                course=course, student__email_verified_at__isnull=False, student__email_reminders=True
            )
            .select_related("student", "course__instructor")
            .annotate(last_event=Max("events__created_at"))
        )
        for enr in qs:
            seen = last_seen(enr)
            if now - seen < every:
                continue
            if enr.last_reminder_at and enr.last_reminder_at > seen and now - enr.last_reminder_at < every:
                continue
            yield enr, (now - seen).days


def send_due(now=None, dry_run: bool = False) -> int:
    now = now or timezone.now()
    base = settings.PUBLIC_BASE_URL
    sent = 0
    for enr, days in list(due(now)):
        if dry_run:
            sent += 1
            continue
        ok = emails.send(
            "reminder",
            enr.student.email,
            enr.student.lang,
            name=enr.student.name,
            course=enr.course.title,
            instructor=enr.course.instructor.display_name,
            days=days,
            link=f"{base}/me/" if base else "",
        )
        if ok:
            Enrollment.objects.filter(pk=enr.pk).update(last_reminder_at=now)
            sent += 1
    return sent
