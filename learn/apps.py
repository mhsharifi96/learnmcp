from django.apps import AppConfig
from django.db.models.signals import post_migrate

INSTRUCTORS_GROUP = "Instructors"

# model -> permission actions granted to the Instructors group
INSTRUCTOR_PERMISSIONS = {
    "course": ["add", "change", "delete", "view"],
    "lesson": ["add", "change", "delete", "view"],
    "quiz": ["add", "change", "delete", "view"],
    "question": ["add", "change", "delete", "view"],
    "enrollment": ["view"],
    "quizattempt": ["view"],
    "answer": ["view", "change"],
    "event": ["view"],
}


def ensure_instructors_group(**kwargs):
    from django.contrib.auth.models import Group, Permission

    group, _ = Group.objects.get_or_create(name=INSTRUCTORS_GROUP)
    codenames = [f"{action}_{model}" for model, actions in INSTRUCTOR_PERMISSIONS.items() for action in actions]
    perms = Permission.objects.filter(content_type__app_label="learn", codename__in=codenames)
    group.permissions.set(perms)
    return group


class LearnConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "learn"
    verbose_name = "learnmcp"

    def ready(self):
        post_migrate.connect(ensure_instructors_group, sender=self)
