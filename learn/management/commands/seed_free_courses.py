"""Create the 255 free public courses of learnmcp/management/free_courses on an academy instructor.

Each course is listed, needs the site admin's approval for new students, and gets its lesson
titles only (no lesson text, no quizzes): the public page shows the syllabus as locked.

Safe to run more than once: courses are matched by title and never overwritten, so later
edits in the admin are kept.

    python manage.py seed_free_courses [--username academy] [--display-name "آکادمی learnmcp"] [--dry-run]
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from learn.apps import ensure_instructors_group
from learn.management.free_courses import COURSES, description
from learn.models import Course, Instructor, Lesson


class Command(BaseCommand):
    help = "Create 255 free public courses (description and locked syllabus) that need admin approval to join."

    def add_arguments(self, parser):
        parser.add_argument("--username", default="academy")
        parser.add_argument("--display-name", default="آکادمی learnmcp")
        parser.add_argument("--dry-run", action="store_true")

    @transaction.atomic
    def handle(self, *args, username, display_name, dry_run=False, **options):
        User = get_user_model()
        user, made = User.objects.get_or_create(username=username, defaults={"is_staff": True})
        if made:
            user.set_unusable_password()
            user.save()
        user.groups.add(ensure_instructors_group())
        instructor, _ = Instructor.objects.get_or_create(user=user, defaults={"display_name": display_name})

        created = 0
        for spec in COURSES:
            course, new = Course.objects.get_or_create(
                instructor=instructor,
                title=spec["title"],
                defaults={"description": description(spec), "listed": True, "requires_approval": True},
            )
            if not new:
                continue
            created += 1
            Lesson.objects.bulk_create(
                Lesson(course=course, order=n, title=title) for n, title in enumerate(spec["lessons"], start=1)
            )
        self.stdout.write(self.style.SUCCESS(f"{created} new courses ({len(COURSES)} in the list)."))
        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write("Dry run: nothing saved.")
