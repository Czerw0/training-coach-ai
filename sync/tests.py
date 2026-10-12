import pytest
from django.core.management import call_command

from coach.dashboard import group_sets
from sync.management.commands.sync_exercises import EXERCISES
from sync.management.commands.sync_garmin import parse_exercise_sets
from sync.models import Exercise


@pytest.mark.django_db
def test_sync_exercises_creates_all_seed_rows():
    call_command("sync_exercises")
    assert Exercise.objects.count() == len(EXERCISES)


@pytest.mark.django_db
def test_sync_exercises_is_idempotent():
    call_command("sync_exercises")
    call_command("sync_exercises")
    assert Exercise.objects.count() == len(EXERCISES)


GARMIN_SETS = {"exerciseSets": [
    {"setType": "ACTIVE", "repetitionCount": 8, "weight": 60000.0,
     "exercises": [{"category": "DEADLIFT", "name": "ROMANIAN_DEADLIFT"}]},
    {"setType": "REST", "repetitionCount": None, "weight": None, "exercises": []},
    {"setType": "ACTIVE", "repetitionCount": 6, "weight": 70000.0,
     "exercises": [{"category": "DEADLIFT", "name": "ROMANIAN_DEADLIFT"}]},
    {"setType": "ACTIVE", "repetitionCount": 10, "weight": None,
     "exercises": [{"category": "PLANK", "name": None}]},
]}


def test_parse_exercise_sets_keeps_active_sets_in_kg():
    sets = parse_exercise_sets(GARMIN_SETS)
    assert sets == [
        {"name": "Romanian Deadlift", "reps": 8, "weight_kg": 60.0},
        {"name": "Romanian Deadlift", "reps": 6, "weight_kg": 70.0},
        {"name": "Plank", "reps": 10, "weight_kg": None},
    ]


def test_parse_exercise_sets_handles_empty_payload():
    assert parse_exercise_sets(None) == []
    assert parse_exercise_sets({}) == []


def test_group_sets_merges_consecutive_sets():
    rows = group_sets(parse_exercise_sets(GARMIN_SETS))
    assert rows[0] == {"name": "Romanian Deadlift", "sets": 2, "reps": [8, 6], "weight_kg": 70.0}
    assert rows[1]["name"] == "Plank" and rows[1]["sets"] == 1
