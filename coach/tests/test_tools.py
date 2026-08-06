import datetime

import pytest

from coach.models import Injury, PlannedExercise, PlannedSession
from coach.tools import (
    create_planned_session,
    get_exercise_detail,
    get_fitness_trend,
    get_resolved_injury_history,
)
from sync.models import DailyStats, Exercise


@pytest.mark.django_db
def test_create_planned_session_rejects_invalid_activity_type():
    d = datetime.date.today()
    result = create_planned_session(
        date=d.isoformat(), weekday=d.strftime("%A"), activity_type="running",
    )
    assert "Invalid input" in result
    assert PlannedSession.objects.count() == 0


@pytest.mark.django_db
def test_create_planned_session_rejects_out_of_range_sets():
    d = datetime.date.today()
    result = create_planned_session(
        date=d.isoformat(), weekday=d.strftime("%A"), activity_type="gym_legs",
        exercises=[{"name": "Barbell Back Squat", "sets": 999, "reps": 6}],
    )
    assert "Invalid input" in result
    assert PlannedSession.objects.count() == 0


@pytest.mark.django_db
def test_create_planned_session_writes_planned_exercise_rows():
    d = datetime.date.today()
    result = create_planned_session(
        date=d.isoformat(), weekday=d.strftime("%A"), activity_type="gym_legs",
        exercises=[
            {"name": "Barbell Back Squat", "sets": 4, "reps": 6, "weight_kg": 80, "notes": "felt strong"},
            {"name": "Romanian Deadlift", "sets": 3, "reps": 8},
        ],
    )
    assert "Planned gym_legs" in result
    session = PlannedSession.objects.get()
    assert session.exercises.count() == 2
    squat = session.exercises.get(name="Barbell Back Squat")
    assert squat.sets == 4 and squat.reps == 6 and squat.weight_kg == 80
    assert squat.notes == "felt strong"


@pytest.mark.django_db
def test_create_planned_session_still_rejects_weekday_mismatch():
    d = datetime.date.today()
    wrong_weekday = "Monday" if d.strftime("%A") != "Monday" else "Tuesday"
    result = create_planned_session(
        date=d.isoformat(), weekday=wrong_weekday, activity_type="cycling",
    )
    assert "mismatch" in result.lower()
    assert PlannedSession.objects.count() == 0


@pytest.mark.django_db
def test_create_planned_session_accepts_mountaineering():
    d = datetime.date.today()
    result = create_planned_session(
        date=d.isoformat(), weekday=d.strftime("%A"), activity_type="mountaineering",
    )
    assert "Planned mountaineering" in result
    assert PlannedSession.objects.get().activity_type == "mountaineering"


@pytest.mark.django_db
def test_create_planned_session_without_exercises_creates_no_planned_exercise_rows():
    d = datetime.date.today()
    create_planned_session(date=d.isoformat(), weekday=d.strftime("%A"), activity_type="cycling")
    assert PlannedExercise.objects.count() == 0


# --- get_exercise_detail ---

@pytest.mark.django_db
def test_get_exercise_detail_includes_progression_and_injury_notes():
    Exercise.objects.create(
        name="Barbell Back Squat", category="legs", target_muscle="quads",
        equipment="barbell", default_sets=4, default_reps=6,
        progression_notes="add 2.5kg per week", injury_notes="avoid with acute knee pain",
        description="Primary lower-body strength movement.",
    )
    result = get_exercise_detail("barbell back squat")   # case-insensitive match
    assert "add 2.5kg per week" in result
    assert "avoid with acute knee pain" in result


@pytest.mark.django_db
def test_get_exercise_detail_no_match_returns_message():
    result = get_exercise_detail("Nonexistent Exercise")
    assert "No exercise" in result


# --- get_fitness_trend ---

@pytest.mark.django_db
def test_get_fitness_trend_returns_recent_vo2max_rows():
    today = datetime.date.today()
    DailyStats.objects.create(date=today, vo2max_cycling=52.0, vo2max_running=48.0, endurance_score=70)
    result = get_fitness_trend()
    assert "52.0" in result or "52" in result


@pytest.mark.django_db
def test_get_fitness_trend_no_data_message():
    result = get_fitness_trend()
    assert "No fitness trend data" in result


# --- get_resolved_injury_history ---

@pytest.mark.django_db
def test_get_resolved_injury_history_includes_recently_resolved():
    today = datetime.date.today()
    Injury.objects.create(
        date_started=today - datetime.timedelta(days=20),
        date_resolved=today - datetime.timedelta(days=5),
        body_part="left wrist", severity="minor", description="mild sprain",
    )
    result = get_resolved_injury_history()
    assert "left wrist" in result


@pytest.mark.django_db
def test_get_resolved_injury_history_excludes_still_active_injury():
    today = datetime.date.today()
    Injury.objects.create(
        date_started=today - datetime.timedelta(days=5),
        date_resolved=None,
        body_part="right knee", severity="moderate", description="still active",
    )
    result = get_resolved_injury_history()
    assert "right knee" not in result
    assert "No resolved injuries" in result
