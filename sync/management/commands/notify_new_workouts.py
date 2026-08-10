import os
from pathlib import Path

import environ
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.utils import timezone

from sync.models import Activity
from coach.agent import chat

env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

EMAIL = env("EMAIL")             # recipient, must match the key in .env
# Sender = the authenticated Gmail account (Gmail rewrites any other From).
# settings.DEFAULT_FROM_EMAIL resolves to EMAIL when SMTP creds are configured.
FROM_ADDRESS = settings.DEFAULT_FROM_EMAIL

# Tag for the ApiUsage rows these turns write, so the auto-generated workout
# emails stay filterable OUT of the interactive-chat cost baseline (the
# experimental control group — see CLAUDE.md). Bump on any prompt/behaviour
# change here, same discipline as CONFIG_VERSION in agent.py.
WORKOUT_EMAIL_CONFIG_VERSION = "workout-email-v1"

# Substring match, mirroring sync_garmin._parse_sport_specifics — robust to
# Garmin typeKey variants (treadmill_running, indoor_cycling, road_biking, ...)
# without having to enumerate every one. "Endurance/structured only": skip
# walks, incidental activity, etc.
ENDURANCE_SUBSTRINGS = (
    "running", "treadmill", "cycling", "biking", "bike",
    "strength", "swimming",
)


def _is_endurance(activity_type):
    t = (activity_type or "").lower()
    return any(s in t for s in ENDURANCE_SUBSTRINGS)


class Command(BaseCommand):
    help = "Email an AI-coach insight for each newly synced endurance/strength workout."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Generate and print insights but don't send email or stamp the DB.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        # Pickup filter: notified_at is null == not yet emailed. The migration
        # backfilled all pre-existing rows, so only genuinely new syncs match.
        # Oldest first so within one run a later workout's context already sees
        # the earlier one's freshly-stored insight.
        pending = Activity.objects.filter(
            notified_at__isnull=True
        ).order_by('start_time')

        sent = 0
        for activity in pending:
            if not _is_endurance(activity.activity_type):
                # Non-endurance: leave notified_at null (nothing to send). It'll
                # be re-scanned each run, but the query is cheap and bounded by
                # how few unnotified rows exist at any time.
                continue

            subject = self._subject(activity)

            try:
                insight = self._generate_insight(activity)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Insight generation failed for {activity.garmin_id} "
                    f"({activity.activity_type}), will retry next run: {e}"
                ))
                continue

            if dry_run:
                self.stdout.write(f"\n--- {subject} ---\n{insight}\n")
                continue

            try:
                send_mail(subject, insight, FROM_ADDRESS, [EMAIL], fail_silently=False)
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Email send failed for {activity.garmin_id}, "
                    f"will retry next run: {e}"
                ))
                continue

            # Stamp only after a fully successful send. If either step above
            # failed we `continue`d without stamping, so the activity is retried
            # on the next run rather than silently dropped.
            activity.coach_insight = insight
            activity.notified_at = timezone.now()
            activity.save(update_fields=['coach_insight', 'notified_at'])
            sent += 1
            self.stdout.write(self.style.SUCCESS(f"  Emailed insight: {subject}"))

        self.stdout.write(self.style.SUCCESS(f"Done. {sent} workout insight(s) sent."))

    def _subject(self, activity):
        when = activity.start_time.date().isoformat() if activity.start_time else "recent"
        name = activity.activity_name or activity.activity_type
        return f"AI Coach — New workout: {name} ({when})"

    def _generate_insight(self, activity):
        """Run one non-interactive coaching turn about this specific workout.

        The activity is already inside recent_activities in the agent's context
        (14-day window), so we point the model at it and let it read the metrics
        + surrounding load/recovery from context rather than re-passing them.
        """
        when = activity.start_time.date().isoformat() if activity.start_time else "today"
        prompt = (
            f"A new {activity.activity_type} workout was just synced from Garmin "
            f"(name: {activity.activity_name or 'n/a'}, date: {when}). It's in "
            "recent_activities in your context. Write a short, friendly email-style "
            "insight about THIS specific workout: what it was, how it went based on "
            "the recorded metrics, and what it means for my current training "
            "(load / ACWR / recovery). Ground every claim in the data in your "
            "context — do not invent numbers or trends that aren't there. Skip "
            "greeting and sign-off boilerplate; just the insight."
        )
        reply, _tools = chat(
            prompt,
            config_version=WORKOUT_EMAIL_CONFIG_VERSION,
            record_recommendation=False,
        )
        return reply
