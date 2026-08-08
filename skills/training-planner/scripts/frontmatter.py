"""Zero-dependency frontmatter parser + session-file locator.

Shared by catalog.py, sessions.py and check_week.py so the parse happens in
exactly one place. Deliberately stdlib-only: this skill has to run identically
on Claude.ai, the API and Claude Code, where PyYAML may not be installed. The
frontmatter in this library only ever uses inline (flow) YAML — `[a, b]` and
`{k: v}` — so a tiny hand-rolled parser is enough. If a file ever needs
block-style or nested YAML, swap this whole module for PyYAML's safe_load
rather than growing it.
"""
import sys
from pathlib import Path


def use_utf8_stdout():
    """Force UTF-8 output so bodies with en/em-dashes and arrows print on any
    console (Windows cp125x consoles otherwise raise UnicodeEncodeError). CLI
    entry points call this; harmless where stdout is already UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


# scripts/ -> parent = skill root (training-planner/)
SKILL_ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = SKILL_ROOT / "reference" / "sessions"
PRINCIPLES_DIR = SKILL_ROOT / "reference" / "principles"

# Keys whose values are inline lists rather than scalars.
_LIST_KEYS = {
    "same_day_conflicts",
    "pairs_well_with",
    "prerequisites",
    "contraindicated_if",
    "see_also",
}
# Keys whose values are inline maps.
_MAP_KEYS = {"load", "spacing_h"}
# Keys whose scalar value should be coerced to int when possible.
_INT_KEYS = {"residual_fatigue_h"}


def _coerce_int(value):
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return value


def _parse_value(key, raw):
    raw = raw.strip()
    if key in _LIST_KEYS:
        inner = raw.strip("[]").strip()
        return [item.strip() for item in inner.split(",") if item.strip()]
    if key in _MAP_KEYS:
        inner = raw.strip("{}").strip()
        out = {}
        for pair in inner.split(","):
            if ":" not in pair:
                continue
            k, _, v = pair.partition(":")
            k, v = k.strip(), v.strip()
            # spacing_h values are hour counts; load axis values stay strings
            out[k] = _coerce_int(v) if key == "spacing_h" else v
        return out
    if key in _INT_KEYS:
        return _coerce_int(raw)
    return raw


def parse(text):
    """Split a `---`-delimited frontmatter block from the body.

    Returns (meta_dict, body_str). A file with no frontmatter yields ({}, text).
    """
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        meta[key] = _parse_value(key, value)
    return meta, parts[2].lstrip("\n")


def session_path(session_id):
    """Map a `category/skill` id to its reference file path (may not exist)."""
    category, _, skill = session_id.partition("/")
    return SESSIONS_DIR / category / f"{skill}.md"


def load_session_meta(session_id):
    """Frontmatter dict for one session, or None if the file is missing."""
    path = session_path(session_id)
    if not path.is_file():
        return None
    meta, _ = parse(path.read_text(encoding="utf-8"))
    return meta


def iter_sessions():
    """Yield (session_id, meta, path) for every leaf under reference/sessions/.

    The directory scan is the single source of truth: dropping a new
    <category>/<skill>.md in makes it discoverable with nothing else to register.
    """
    if not SESSIONS_DIR.is_dir():
        return
    for category_dir in sorted(SESSIONS_DIR.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue
        for md in sorted(category_dir.glob("*.md")):
            meta, _ = parse(md.read_text(encoding="utf-8"))
            yield f"{category_dir.name}/{md.stem}", meta, md
