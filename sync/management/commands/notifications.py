import os
from pathlib import Path
import environ
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from coach.models import PlannedSession

env = environ.Env(DEBUG=(bool, False))
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

EMAIL = env("EMAIL")   # must match the key in your .env exactly


class Command(BaseCommand):
    help = "Send the weekly training schedule by email"

    def handle(self, *args, **options):
        schedule = PlannedSession.objects.all().order_by('date')
        
        # Build one text line per planned session
        lines = []
        for s in schedule:
            label = s.title or s.activity_type
            lines.append(f"{s.date} — {label}")

        body = "Hi,\n\nThis is how your training week looks:\n\n" + "\n".join(lines)

        self.stdout.write(body)   # print to terminal for testing

        send_mail(
            "AI Coach — Weekly Schedule",
            body,
            "ai-coach.noreply@gmail.com",
            [EMAIL],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS("Email sent."))