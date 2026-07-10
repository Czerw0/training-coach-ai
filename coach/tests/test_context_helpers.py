from coach.agent import compute_cost
from coach.context import _round, _clean_activities, _summarise_weather
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

# def test_one_million_input_tokens_costs_one_dollar():
#     assert compute_cost(1_000_000, 0, 0, 0) == 1.0

# def test_mixed_turn():
#     # 100k in + 10k out: 0.10 + 0.05 = 0.15
#     assert compute_cost(100_000, 0, 0, 10_000) == 0.15