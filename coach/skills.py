"""Prompt assembly: core instructions always loaded, "skill" blocks added
only when triage says a turn needs them. Only WORKOUT_SKILL exists so far —
start coarse, split further only once a concrete case needs it.

Safety-critical stuff (injury/anti-fabrication/dates) always stays in
CORE_INSTRUCTIONS, never conditional on triage.

CORE_INSTRUCTIONS/WORKOUT_SKILL are sliced out of the real INSTRUCTIONS
string, not retyped — assemble_all() reproduces INSTRUCTIONS byte-for-byte
by construction, and a future edit removing the marker lines fails loudly
(ValueError at import) instead of drifting silently.
"""
from coach.agent import INSTRUCTIONS

_SKILL_START_MARKER = "- For indoor cycling, pick a workout from indoor_workouts"
_SKILL_END_MARKER = "  description for an overall session-level comment, not per-exercise detail.\n"

_skill_start = INSTRUCTIONS.index(_SKILL_START_MARKER)
_skill_end = INSTRUCTIONS.index(_SKILL_END_MARKER) + len(_SKILL_END_MARKER)

_prefix = INSTRUCTIONS[:_skill_start]
_suffix = INSTRUCTIONS[_skill_end:]

WORKOUT_SKILL = INSTRUCTIONS[_skill_start:_skill_end]
CORE_INSTRUCTIONS = _prefix + _suffix


def assemble_all():
    """Core + every skill — used when triage is off, must equal INSTRUCTIONS exactly."""
    return _prefix + WORKOUT_SKILL + _suffix


def assemble_instructions(classification):
    """classification: whatever classify_turn() (triage.py) returns."""
    if "workout" in classification.get("skills", []):
        return _prefix + WORKOUT_SKILL + _suffix
    return CORE_INSTRUCTIONS
