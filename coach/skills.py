"""Prompt assembly for turn triage: core instructions always, skill blocks
only when needed. Blocks are sliced from INSTRUCTIONS by marker (ValueError at
import if a marker disappears). Safety rules always stay in core.
"""
from coach.agent import INSTRUCTIONS

_SKILL_START_MARKER = "- For indoor cycling, pick a workout from indoor_workouts"
_SKILL_END_MARKER = "  card (see SESSION DETAIL).\n"

_skill_start = INSTRUCTIONS.index(_SKILL_START_MARKER)
_skill_end = INSTRUCTIONS.index(_SKILL_END_MARKER) + len(_SKILL_END_MARKER)

_prefix = INSTRUCTIONS[:_skill_start]
_suffix = INSTRUCTIONS[_skill_end:]

WORKOUT_SKILL = INSTRUCTIONS[_skill_start:_skill_end]
CORE_INSTRUCTIONS = _prefix + _suffix


def assemble_all():
    """Core + every skill — used when triage is off, must equal INSTRUCTIONS exactly."""
    return _prefix + WORKOUT_SKILL + _suffix


def assemble_instructions(classification, text=None):
    """classification: whatever classify_turn() (triage.py) returns.
    text: a user's own prompt. It is sliced by the same markers when it still
    has them; one that doesn't is sent whole (never a ValueError mid-chat)."""
    if text is None or text == INSTRUCTIONS:
        prefix, skill, suffix = _prefix, WORKOUT_SKILL, _suffix
    else:
        try:
            start = text.index(_SKILL_START_MARKER)
            end = text.index(_SKILL_END_MARKER, start) + len(_SKILL_END_MARKER)
        except ValueError:
            return text
        prefix, skill, suffix = text[:start], text[start:end], text[end:]
    if "workout" in classification.get("skills", []):
        return prefix + skill + suffix
    return prefix + suffix
