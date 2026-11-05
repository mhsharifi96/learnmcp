import time

from django.core.management.base import BaseCommand

from learn.services import reminders


class Command(BaseCommand):
    help = "Email students who haven't studied a class for the instructor's chosen number of days."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Count reminders without sending.")
        parser.add_argument(
            "--loop", type=int, default=0, metavar="SECONDS", help="Keep running, checking every SECONDS."
        )

    def handle(self, *args, dry_run=False, loop=0, **options):
        while True:
            n = reminders.send_due(dry_run=dry_run)
            self.stdout.write(f"{'Would send' if dry_run else 'Sent'} {n} reminder(s).")
            if not loop:
                return
            time.sleep(loop)
