"""Prompt assembly for turn triage: core instructions always, skill blocks
only when needed. Blocks are sliced from INSTRUCTIONS by marker (ValueError at
import if a marker disappears). Safety rules always stay in core.
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
