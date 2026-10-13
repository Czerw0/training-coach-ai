"""Which coach instructions a chat turn runs on.

The default — INSTRUCTIONS in coach/agent.py, versioned in git (PROMPT_VERSION)
— is the same for every athlete and says nothing about any one of them. Each
user can add their own section (CoachPrompt, append-only versions; empty = none),
which is appended under THIS ATHLETE. Their section never replaces the default,
so improvements to the default reach everyone.

The tag written to ApiUsage.prompt_version:
  default only        -> "v2.0.0@1a2b3c4d"                  (PROMPT_TAG)
  default + section   -> "v2.0.0@1a2b3c4d+u3/v2@5e6f7a8b"   (user id, their version, hash)
"""
import hashlib

from django.db import IntegrityError, transaction

from coach import profile_changes
from coach.agent import INSTRUCTIONS, PROMPT_TAG, PROMPT_VERSION
from coach.models import CoachPrompt

MAX_CHARS = 20_000

ATHLETE_HEADER = (
    "\n\n=== THIS ATHLETE ===\n"
    "Written by the athlete. It refines everything above for them; the safety rules,\n"
    "athlete_rules and NEVER FAKE ACTIONS still apply.\n\n"
)


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def latest(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return CoachPrompt.objects.filter(user=user).order_by("-version").first()


def compose(section):
    return INSTRUCTIONS + ATHLETE_HEADER + section.strip() if section and section.strip() else INSTRUCTIONS


def active_prompt(user):
    """(full system instructions, tag) for this user's next chat turn."""
    row = latest(user)
    if not row or not row.text.strip():
        return INSTRUCTIONS, PROMPT_TAG
    return compose(row.text), f"{PROMPT_TAG}+u{user.id}/v{row.version}@{text_hash(row.text)}"


def save_version(user, text, note=""):
    """Append a version of the user's section ("" removes it). Returns
    (row, created) — created is False when nothing changed."""
    text = (text or "").replace("\r\n", "\n").strip()
    current = latest(user)
    old = current.text if current else ""
    if old == text:
        return current, False
    for _ in range(3):   # unique (user, version) settles a double-click race
        try:
            with transaction.atomic():
                version = (current.version if current else 0) + 1
                row = CoachPrompt.objects.create(user=user, version=version, text=text, note=note[:200],
                                                 based_on=PROMPT_VERSION)
                profile_changes.record_text(user, "coach_instructions", old, text)
                return row, True
        except IntegrityError:
            current = latest(user)
    raise IntegrityError("Could not save a new version, try again.")


def summary(user):
    """Settings page payload."""
    rows = list(CoachPrompt.objects.filter(user=user).order_by("-version")[:30])
    active = rows[0] if rows else None
    return {
        "text": active.text if active else "", "tag": active_prompt(user)[1],
        "has_section": bool(active and active.text.strip()),
        "version": active.version if active else 0,
        "default_text": INSTRUCTIONS, "default_version": PROMPT_VERSION, "max_chars": MAX_CHARS,
        "versions": [{"version": r.version, "created_at": r.created_at.isoformat(), "empty": not r.text.strip(),
                      "chars": len(r.text), "note": r.note, "active": r is active} for r in rows],
    }
