"""Filesystem-backed training-skill library (planning/scheduling methodology).

Distinct from coach/skills.py (prompt-slicing / turn triage). This module reads
the session leaves of the portable training-planner skill on demand, so their
methodology isn't carried in context every turn — "index always, detail on
demand", same as get_workout_detail / get_exercise_detail.

This hand-built agent loop is NOT a skill-aware runtime, so it can't auto-load
the skill's SKILL.md — it only sees what build_context() puts in the data block
and what tools return. This module is that bridge: it points at the skill's
`reference/sessions/` tree and surfaces the leaves' frontmatter as an index.
The skill's principles/ and scripts/ (e.g. check_week.py) are NOT consumed here.

The directory scan is the single source of truth: the context index and the
load_training_skill tool's allow-list both come from list_skills(), so a new
session leaf is discoverable with nothing else to register.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# coach/training_skills.py -> parent.parent = repo root; the portable skill and
# its session leaves / principles / checker script all live under it.
_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills" / "training-planner"
SKILLS_DIR = _SKILL_ROOT / "reference" / "sessions"       # one leaf per <category>/<skill>.md
PRINCIPLES_DIR = _SKILL_ROOT / "reference" / "principles"
_CHECK_WEEK = _SKILL_ROOT / "scripts" / "check_week.py"

# category/skill segments must be simple slugs — this is the guard against
# path traversal, since both come straight from model output
_SLUG = re.compile(r"^[a-z0-9-]+$")


def _parse_frontmatter(text):
    """Split a `---`-delimited YAML-ish frontmatter block from the body.

    Returns (meta_dict, body). Deliberately tiny (key: value lines only) to
    avoid a PyYAML dependency for what is a fixed, controlled format.
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, parts[2].lstrip("\n")


def list_skills():
    """Every loadable skill as {category, skill, description}, sorted.

    Derived by scanning SKILLS_DIR/<category>/<skill>.md — the top-level
    SKILL.md index is documentation and is skipped here.
    """
    out = []
    if not SKILLS_DIR.is_dir():
        return out
    for category_dir in sorted(SKILLS_DIR.iterdir()):
        if not category_dir.is_dir():
            continue
        for md in sorted(category_dir.glob("*.md")):
            meta, _ = _parse_frontmatter(md.read_text(encoding="utf-8"))
            out.append({
                "category": category_dir.name,
                "skill": md.stem,
                "description": meta.get("description", ""),
            })
    return out


def load_skill(category, skill):
    """Full methodology (body, frontmatter stripped) for one skill.

    Returns an error string (not an exception) on a bad slug or missing file so
    the model gets it back as a tool result and can self-correct — same
    convention as the other read tools.
    """
    if not (_SLUG.match(category or "") and _SLUG.match(skill or "")):
        return (
            f"Invalid skill reference '{category}/{skill}'. "
            "Use exact category and skill from the training_skills index."
        )
    path = (SKILLS_DIR / category / f"{skill}.md").resolve()
    # defence in depth: the resolved path must stay inside SKILLS_DIR
    if not path.is_relative_to(SKILLS_DIR.resolve()) or not path.is_file():
        available = ", ".join(f"{s['category']}/{s['skill']}" for s in list_skills())
        return f"No training skill '{category}/{skill}'. Available: {available}."
    _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
    return body.strip()


def load_principles():
    """The skill's shared cross-cutting reasoning (both principles files).

    Fatigue axes, interference, load progression, readiness/downgrade, deload
    and taper — the "why" the session leaves defer to. Meant to be read once
    per planning turn before any leaf. Returned concatenated, load-and-recovery
    first (its filename sorts ahead of planning-the-week).
    """
    if not PRINCIPLES_DIR.is_dir():
        return "No training principles available."
    parts = []
    for md in sorted(PRINCIPLES_DIR.glob("*.md")):
        _, body = _parse_frontmatter(md.read_text(encoding="utf-8"))
        parts.append(body.strip())
    return "\n\n---\n\n".join(parts) if parts else "No training principles available."


def check_week(sessions):
    """Run the skill's deterministic week checker on a proposed schedule.

    Delegates to the skill's own scripts/check_week.py via subprocess so the
    rules live in exactly one place (the portable skill), not reimplemented
    here. `sessions` is a list of {"id": "category/skill", "start": "<ISO-8601>"}.
    Returns the checker's text report (errors + warnings + counts) — never
    raises, so the model gets a usable tool result either way.
    """
    try:
        payload = json.dumps([
            {"id": s.get("id"), "start": s.get("start")} for s in sessions
        ])
    except (TypeError, AttributeError):
        return "Invalid week: expected a list of {id, start} objects."
    try:
        proc = subprocess.run(
            [sys.executable, str(_CHECK_WEEK), "-", "--format", "text"],
            input=payload, capture_output=True, encoding="utf-8", timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as e:
        return f"Could not run the week checker: {e}"
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    return out or err or "The week checker returned no output."
