import pytest

from coach.context import _round, _clean_activities, _summarise_weather, build_context
from django.core.exceptions import ValidationError

from sync.models import Exercise, UserProfile
from datetime import datetime

def test_round_returns_none_for_none():
    assert _round(None) is None

def test_round_rounds_to_one_digit():
    assert _round(3.14159) == 3.1

def make_activity(**overrides):
    base = {
        "start_time": datetime(2026, 6, 1, 10, 0),
        "activity_type": "cycling",
        "duration_seconds": 5400,     
        "distance_meters": 30000,     
        "avg_hr": 145,
        "training_load": 80.0,
        "training_effect_label": "AEROBIC_BASE",
        "tss": 50.0,
        "avg_power": 170,
        "normalized_power": 180,
    }
    base.update(overrides)  
    return base

def test_clean_converts_units():
    cleaned = _clean_activities([make_activity()])
    assert cleaned[0]["duration_min"] == 90    
    assert cleaned[0]["distance_km"] == 30.0

def test_clean_none_distance_stays_none():
    cleaned = _clean_activities([make_activity(distance_meters=None)])
    assert cleaned[0]["distance_km"] is None

def test_clean_none_avg_hr_stays_none():
    cleaned = _clean_activities([make_activity(avg_hr=None)])
    assert cleaned[0]["avg_hr"] is None



def make_weather_hour(**overrides):
    base = {
        "datetime": datetime(2026, 6, 1, 10),
        "temp": 20,
        "precipitation_probability": 0,
        "wind_speed": 5,
        "weather_code": 0,
    }
    base.update(overrides)
    return base

def test_weather_hour_12_is_afternoon_not_morning():
    hours = [make_weather_hour(datetime=datetime(2026, 6, 1, 12))]
    summary = _summarise_weather(hours)
    blocks = summary["2026-06-01"]
    assert "afternoon (12-18)" in blocks
    assert "morning (06-12)" not in blocks


@pytest.mark.django_db
def test_build_context_excludes_fitness_trend_and_resolved_injuries():
    context = build_context()
    assert "fitness_trend" not in context
    assert "recent_resolved_injuries" not in context


@pytest.mark.django_db
def test_build_context_includes_exercise_library_index_without_progression_notes():
    Exercise.objects.create(
        name="Barbell Back Squat", category="legs", target_muscle="quads",
        equipment="barbell", progression_notes="add 2.5kg/week",
        injury_notes="avoid with acute knee pain",
    )
    context = build_context()
    library = context["exercise_library"]
    assert len(library) == 1
    entry = library[0]
    assert entry["name"] == "Barbell Back Squat"
    assert "progression_notes" not in entry
    assert "injury_notes" not in entry


ZONES = [
    {"zone": "Z1", "min_bpm": 0, "max_bpm": 150},
    {"zone": "Z2", "min_bpm": 151, "max_bpm": 165},
    {"zone": "Z5", "min_bpm": 196, "max_bpm": None},
]


@pytest.mark.django_db
def test_build_context_includes_hr_zones():
    UserProfile.objects.create(hr_zones=ZONES)
    assert build_context()["user_profile"]["hr_zones"] == ZONES


def test_hr_zones_valid_passes_clean():
    UserProfile(hr_zones=ZONES).clean()


def test_hr_zones_overlap_fails_clean():
    bad = [{"zone": "Z1", "min_bpm": 0, "max_bpm": 150},
           {"zone": "Z2", "min_bpm": 150, "max_bpm": 165}]
    with pytest.raises(ValidationError):
        UserProfile(hr_zones=bad).clean()


def test_hr_zones_wrong_shape_fails_clean():
    with pytest.raises(ValidationError):
        UserProfile(hr_zones=[{"zone": "Z1", "low": 0}]).clean()
