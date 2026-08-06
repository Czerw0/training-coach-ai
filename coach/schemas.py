"""Pydantic schemas for LLM tool inputs that write to the DB — model output
is a claim, not a fact, until it passes one of these. Validation errors come
back as a plain string (never raised), same convention as validate_session_date."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, ValidationError

ACTIVITY_TYPES = Literal[
    "cycling", "gym_legs", "gym_upper", "skating", "tennis",
    "skiing", "mountaineering", "rest", "other",
]
INTENSITIES = Literal["", "easy", "moderate", "hard"]


class PlannedExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    sets: Optional[int] = Field(default=None, ge=1, le=20)
    reps: Optional[int] = Field(default=None, ge=1, le=200)
    weight_kg: Optional[float] = Field(default=None, ge=0, le=500)
    notes: str = Field(default="", max_length=500)


class PlannedSessionIn(BaseModel):
    date: str
    weekday: str
    activity_type: ACTIVITY_TYPES
    title: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=2000)
    duration_minutes: Optional[int] = Field(default=None, ge=0, le=600)
    intensity: INTENSITIES = ""
    exercises: list[PlannedExerciseIn] = Field(default_factory=list)


class ClearPlannedSessionsIn(BaseModel):
    date: str
    weekday: str


def format_validation_error(exc: ValidationError) -> str:
    """One-line-per-error string, safe to return as a tool result."""
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"])
        lines.append(f"{loc}: {err['msg']}")
    return "Invalid input — " + "; ".join(lines)
