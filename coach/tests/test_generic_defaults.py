"""The default layer (prompt, skills, insights prompt) is the same for every
athlete. Anything about one person belongs in their rules, notes or own
section — this test fails if it leaks back into the defaults."""
from pathlib import Path

import pytest

from coach import agent, insights

SKILL_ROOT = Path(__file__).resolve().parents[2] / "skills" / "training-planner"

PERSONAL = [
    "warsaw", "innsbruck", "forerunner", "edge 840", "hrm pro",
    "this athlete —", "for this athlete", "skating instruction", "documented imbalance",
    "knee history", "one run per week", "two runs per week", "north star",
    "sleep problems)",   # "(the athlete has recurring sleep problems)"
]


def _defaults():
    yield "agent.INSTRUCTIONS", agent.INSTRUCTIONS
    yield "insights.SYSTEM", insights.SYSTEM
    for md in sorted(SKILL_ROOT.rglob("*.md")):
        yield str(md.relative_to(SKILL_ROOT)), md.read_text(encoding="utf-8")


@pytest.mark.parametrize("name,text", list(_defaults()), ids=lambda v: v if isinstance(v, str) and len(v) < 80 else "")
def test_default_layer_has_nothing_about_one_athlete(name, text):
    low = text.lower()
    leaks = [w for w in PERSONAL if w in low]
    assert not leaks, f"{name} mentions {leaks} — move it to the athlete's rules/notes/section"


def test_no_leaf_hard_codes_a_weekly_cap():
    leaves = [md for md in (SKILL_ROOT / "reference" / "sessions").rglob("*.md")
              if "category_max_per_week" in md.read_text(encoding="utf-8")]
    assert leaves == [], "personal caps live in athlete_rules.weekly_caps"
