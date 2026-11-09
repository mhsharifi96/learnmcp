from django.db import migrations, models
from django.db.models import F


def approve_existing(apps, schema_editor):
    Enrollment = apps.get_model("learn", "Enrollment")
    Enrollment.objects.filter(approved_at__isnull=True).update(approved_at=F("joined_at"))


class Migration(migrations.Migration):
    dependencies = [("learn", "0009_course_image")]

    operations = [
        migrations.AddField(
            model_name="course",
            name="requires_approval",
            field=models.BooleanField(
                default=False,
                help_text="New students wait for a site admin to approve them before lessons and quizzes open.",
            ),
        ),
        migrations.AddField(
            model_name="enrollment",
            name="approved_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Empty while the student waits for admin approval (classes that need it).",
            ),
        ),
        migrations.RunPython(approve_existing, migrations.RunPython.noop),
    ]
