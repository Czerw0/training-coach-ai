"""Prompt v2.0.0 split the default instructions into a generic part (code) and
the athlete's own section (CoachPrompt, appended under THIS ATHLETE).

Until now the "default" was written for one athlete, and a saved CoachPrompt was
a full copy that replaced it. For every account that exists now, this appends a
new version holding:
  - what used to be in the default and the skills about this athlete
    (coach/prompt_archive/athlete_layer_2026-10-13.txt), so their coaching keeps
    that context, and
  - their own edits to a full copy, as the lines they added to v1.7.0.
Old versions stay in the history. Accounts created later start with no section.
"""
import difflib
from pathlib import Path

from django.conf import settings
from django.db import migrations

ARCHIVE = Path(__file__).resolve().parent.parent / "prompt_archive"
FULL_COPY_MARKER = "=== TOOLS — ACT, DON'T JUST TALK ==="


def _added_lines(old, new):
    a = [line.rstrip() for line in old.splitlines()]
    b = [line.rstrip() for line in new.splitlines()]
    out = []
    for op, _, _, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op in ("replace", "insert"):
            out += [line for line in b[j1:j2] if line.strip()]
    return out


def split(apps, schema_editor):
    CoachPrompt = apps.get_model("coach", "CoachPrompt")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    old_default = (ARCHIVE / "v1.7.0.txt").read_text(encoding="utf-8")
    moved = (ARCHIVE / "athlete_layer_2026-10-13.txt").read_text(encoding="utf-8").strip()
    for user in User.objects.all():
        latest = CoachPrompt.objects.filter(user=user).order_by("-version").first()
        own = []
        if latest and FULL_COPY_MARKER in latest.text:
            own = _added_lines(old_default, latest.text)
        elif latest and latest.text.strip():
            own = [latest.text.strip()]
        text = moved
        if own:
            text += ("\n\nMY OWN EDITS TO THE OLD INSTRUCTIONS\n"
                     "(lines I had added to my full copy — review, some are now covered by the default)\n"
                     + "\n".join(own))
        CoachPrompt.objects.create(user=user, version=(latest.version if latest else 0) + 1, text=text,
                                   note="v2 split: your part of the old default + your edits", based_on="v2.0.0")


class Migration(migrations.Migration):

    dependencies = [
        ('coach', '0024_profilechange_prompt_based_on'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(split, migrations.RunPython.noop),
    ]
