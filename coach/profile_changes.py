"""Hand-made changes to the profile and the coach instructions, kept so the
coach can see *what* changed (context key `recent_profile_changes`) instead of
only the current state. Recorded by the Settings views, not by agent tools."""
import datetime as dt
import difflib

from django.utils import timezone

from coach.models import ProfileChange

MAX_CHARS = 1500     # per side of one change in the context
CONTEXT_DAYS = 14
CONTEXT_LIMIT = 10


def _lines(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


def text_diff(old, new):
    """(added, removed) lines, in order. Whitespace-only edits don't count."""
    a, b = _lines(old), _lines(new)
    added, removed = [], []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op in ("replace", "delete"):
            removed += a[i1:i2]
        if op in ("replace", "insert"):
            added += b[j1:j2]
    return added, removed


def record_text(user, field, old, new):
    added, removed = text_diff(old, new)
    if not added and not removed:
        return None
    return ProfileChange.objects.create(user=user, field=field, added="\n".join(added), removed="\n".join(removed))


def record_value(user, field, old, new):
    if old == new:
        return None
    return ProfileChange.objects.create(user=user, field=field, added="" if new is None else str(new),
                                        removed="" if old is None else str(old))


def _cut(text):
    return text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + " …[cut]"


def recent(now=None):
    """Newest first, for the agent context."""
    now = now or timezone.now()
    rows = ProfileChange.objects.filter(created_at__gte=now - dt.timedelta(days=CONTEXT_DAYS))[:CONTEXT_LIMIT]
    return [{"when": timezone.localtime(r.created_at).strftime("%Y-%m-%d %H:%M"), "field": r.field,
             "added": _cut(r.added), "removed": _cut(r.removed)} for r in rows]
