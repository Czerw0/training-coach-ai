"""When the scheduled GitHub Actions syncs run (UTC hours from the workflow
crons — a test keeps them in sync with .github/workflows/*.yml)."""
import datetime as dt

GARMIN_HOURS_UTC = (4, 6, 8, 10, 12, 14, 16, 18, 21)
WEATHER_HOURS_UTC = (5, 11, 17)


def next_run(hours, now):
    """First scheduled run strictly after `now` (aware datetime, any tz)."""
    now = now.astimezone(dt.timezone.utc)
    for day in (0, 1):
        base = (now + dt.timedelta(days=day)).replace(minute=0, second=0, microsecond=0)
        for h in hours:
            slot = base.replace(hour=h)
            if slot > now:
                return slot
    raise ValueError("empty schedule")


def previous_run(hours, now):
    """Last scheduled run at or before `now`."""
    now = now.astimezone(dt.timezone.utc)
    for day in (0, -1):
        base = (now + dt.timedelta(days=day)).replace(minute=0, second=0, microsecond=0)
        for h in reversed(hours):
            slot = base.replace(hour=h)
            if slot <= now:
                return slot
    raise ValueError("empty schedule")
