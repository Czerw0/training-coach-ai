"""Which coach instructions a chat turn runs on.

Every user starts on the default — INSTRUCTIONS in coach/agent.py, versioned in
git (PROMPT_VERSION). A user can save their own versions (CoachPrompt, append
only); the newest one wins, and an empty one means "back to the default".

The tag written to ApiUsage.prompt_version tells the two apart:
  default  -> "v1.7.0@1a2b3c4d"          (PROMPT_TAG)
  custom   -> "u3/v2@5e6f7a8b"           (user id, user's version, text hash)
"""
import hashlib

from django.db import IntegrityError, transaction

from coach.agent import INSTRUCTIONS, PROMPT_TAG, PROMPT_VERSION
from coach import profile_changes
from coach.models import CoachPrompt

MAX_CHARS = 60_000

# lines whose removal is allowed but worth a warning — they carry the rules
# that keep the coach from inventing numbers or dates
GUARDRAILS = {
    "=== DATES — READ, DON'T CALCULATE ===": "the dates section (the coach copies dates from the data instead of calculating them)",
    "Never invent\n  watt numbers.": "the rule against inventing watt numbers",
}


def text_hash(text):
    return hashlib.sha256(text.encode()).hexdigest()[:8]


def latest(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return None
    return CoachPrompt.objects.filter(user=user).order_by("-version").first()


def active_prompt(user):
    """(text, tag) for this user's next chat turn."""
    row = latest(user)
    if not row or not row.text:
        return INSTRUCTIONS, PROMPT_TAG
    return row.text, f"u{user.id}/v{row.version}@{text_hash(row.text)}"


def warnings_for(text):
    if not text:
        return []
    return [f"Removed {label}." for marker, label in GUARDRAILS.items()
            if marker in INSTRUCTIONS and marker not in text]


def save_version(user, text, note=""):
    """Append a version. Text equal to the default is stored as "" (default),
    so a later change to INSTRUCTIONS still reaches this user. Returns
    (row, created) — created is False when nothing changed."""
    text = (text or "").replace("\r\n", "\n")
    if text.strip() == INSTRUCTIONS.strip():
        text = ""
    current = latest(user)
    if (current.text if current else "") == text:
        return current, False
    for _ in range(3):   # unique (user, version) settles a double-click race
        try:
            with transaction.atomic():
                version = (current.version if current else 0) + 1
                row = CoachPrompt.objects.create(user=user, version=version, text=text, note=note[:200],
                                                 based_on=PROMPT_VERSION)
                profile_changes.record_text(user, "coach_instructions",
                                            (current.text if current else "") or INSTRUCTIONS, text or INSTRUCTIONS)
                return row, True
        except IntegrityError:
            current = latest(user)
    raise IntegrityError("Could not save a new prompt version, try again.")


def summary(user):
    """Settings page payload."""
    rows = list(CoachPrompt.objects.filter(user=user).order_by("-version")[:30])
    text, tag = active_prompt(user)
    active = rows[0] if rows else None
    return {
        "text": text, "tag": tag, "is_default": not (active and active.text),
        "version": active.version if active else 0,
        "default_text": INSTRUCTIONS, "default_version": PROMPT_VERSION, "default_tag": PROMPT_TAG,
        "max_chars": MAX_CHARS, "warnings": warnings_for(active.text if active else ""),
        # the default moved on since this custom version was saved
        "default_updated": bool(active and active.text and active.based_on and active.based_on != PROMPT_VERSION),
        "based_on": active.based_on if active else "",
        # lines of the current default your version doesn't have (new rules, or ones you removed)
        "missing_default_lines": profile_changes.text_diff(active.text, INSTRUCTIONS)[0] if active and active.text else [],
        "versions": [{"version": r.version, "created_at": r.created_at.isoformat(), "is_default": not r.text,
                      "chars": len(r.text) if r.text else len(INSTRUCTIONS), "note": r.note,
                      "active": r is active} for r in rows],
    }
