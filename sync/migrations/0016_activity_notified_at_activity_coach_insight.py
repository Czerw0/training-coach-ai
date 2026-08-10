from django.db import migrations, models
from django.utils import timezone


def mark_existing_notified(apps, schema_editor):
    """Treat every activity that exists BEFORE this feature ships as
    already-notified, so the first `notify_new_workouts` run only picks up
    genuinely new syncs instead of emailing the entire back catalogue."""
    Activity = apps.get_model('sync', 'Activity')
    Activity.objects.filter(notified_at__isnull=True).update(notified_at=timezone.now())


class Migration(migrations.Migration):

    dependencies = [
        ('sync', '0015_exercise'),
    ]

    operations = [
        migrations.AddField(
            model_name='activity',
            name='notified_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='activity',
            name='coach_insight',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.RunPython(mark_existing_notified, migrations.RunPython.noop),
    ]
