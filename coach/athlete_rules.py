"""Per-athlete rules the code enforces — the personal half of what used to be
hard-coded in the prompt and the skills (a weekly run cap, "no bike here").

Stored as JSON on UserProfile.rules and validated here. The week checker and
create_planned_session read them, so a rule holds even when the model forgets
it — same idea as validate_session_date for dates.
"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

# activity groups: the skill categories plus the other calendar activity types
Group = Literal["cycling", "running", "gym", "plyometrics", "skating", "tennis", "skiing", "mountaineering"]
GROUPS = list(Group.__args__)

# create_planned_session activity_type -> group (identity when not listed)
ACTIVITY_GROUP = {"gym_legs": "gym", "gym_upper": "gym"}


class AthleteRules(BaseModel):
    # at most N sessions of a group in any rolling 7 days
    weekly_caps: dict[Group, int] = Field(default_factory=dict)
    # not possible right now (no equipment, paused by choice) — never prescribed
    unavailable: list[Group] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list, max_length=8)
    # what the usual light days (UserProfile.instruction_days) are, e.g. "Skating instruction"
    light_day_label: str = Field(default="", max_length=60)

    @field_validator("weekly_caps")
    @classmethod
    def _caps_in_range(cls, v):
        for group, n in v.items():
            if not 0 <= n <= 14:
                raise ValueError(f"weekly cap for {group} must be 0–14")
        return v

    @field_validator("focus_areas")
    @classmethod
    def _clean_focus(cls, v):
        out = [s.strip()[:40] for s in v if s and s.strip()]
        return list(dict.fromkeys(out))

    @field_validator("unavailable")
    @classmethod
    def _dedupe(cls, v):
        return list(dict.fromkeys(v))


def load(profile=None):
    """Rules of the (single, for now) athlete profile. Bad stored JSON -> no rules,
    never a crash in the middle of a chat."""
    if profile is None:
        from sync.models import UserProfile
        profile = UserProfile.objects.filter(pk=1).first()
    try:
        return AthleteRules.model_validate((profile.rules if profile else None) or {})
    except ValidationError:
        return AthleteRules()


def group_of(activity_type):
    return ACTIVITY_GROUP.get(activity_type, activity_type)


def blocked(activity_type, rules=None):
    """Error message for the model if this activity is unavailable, else None."""
    rules = rules or load()
    group = group_of(activity_type)
    if group in rules.unavailable:
        return (f"Not written: {group} is marked unavailable in the athlete's rules "
                f"(Settings -> Rules). Pick an activity they can do now.")
    return None


def for_checker(rules=None):
    """The part of the rules the week checker enforces."""
    rules = rules or load()
    return {"weekly_caps": dict(rules.weekly_caps), "unavailable": list(rules.unavailable)}


def as_context(rules=None):
    return (rules or load()).model_dump()


def cap_for(group, rules=None) -> Optional[int]:
    return (rules or load()).weekly_caps.get(group)
