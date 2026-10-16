"""Bridge between the agent and skills/training-planner: an index for the
context, on-demand loading of session leaves and principles, and the week
checker. The directory scan is the single source of truth — a new leaf .md is
discoverable with nothing else to register.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills" / "training-planner"
SKILLS_DIR = _SKILL_ROOT / "reference" / "sessions"       # one leaf per <category>/<skill>.md
PRINCIPLES_DIR = _SKILL_ROOT / "reference" / "principles"
_CHECK_WEEK = _SKILL_ROOT / "scripts" / "check_week.py"

# path-traversal guard: category/skill come straight from model output
_SLUG = re.compile(r"^[a-z0-9-]+$")


def _parse_frontmatter(text):
    """(meta_dict, body) — key: value lines only, avoids a PyYAML dependency."""
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
    """Every loadable skill as {category, skill, description}, sorted."""
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
    """Skill body, or an error string the model can self-correct from."""
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
    """Both principles files concatenated (fatigue, progression, readiness, taper)."""
    if not PRINCIPLES_DIR.is_dir():
        return "No training principles available."
    parts = []
    for md in sorted(PRINCIPLES_DIR.glob("*.md")):
        _, body = _parse_frontmatter(md.read_text(encoding="utf-8"))
        parts.append(body.strip())
    return "\n\n---\n\n".join(parts) if parts else "No training principles available."


def check_week(sessions, rules=None):
    """Run the skill's own scripts/check_week.py, so the rules live in one place.

    sessions: [{"id": "category/skill", "start": "<ISO-8601>", "minutes": N?}].
    rules: the athlete's {"weekly_caps", "unavailable", "max_weekly_increase_pct"}
    (coach/athlete_rules.py) + "recent_weekly_minutes". Never raises.
    """
    try:
        week = [{"id": s.get("id"), "start": s.get("start"), "minutes": s.get("minutes")} for s in sessions]
        payload = json.dumps({"sessions": week, "rules": rules or {}})
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
