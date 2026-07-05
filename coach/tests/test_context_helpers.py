from coach.context import _round, _clean_activities

def test_round_returns_none_for_none():
    assert _round(None) is None

def test_round_rounds_to_one_digit():
    assert _round(3.14159) == 3.1

def test_clean_activities():
    activities = [
        {"date": "2023-01-01", "activity_type": "cycling", "duration_minutes": 60},
        {"date": "2023-01-02", "activity_type": "gym_legs", "duration_minutes": 45},
        {"date": "2023-01-03", "activity_type": "skating", "duration_minutes": 30},
    ]
    cleaned = _clean_activities(activities)
    assert len(cleaned) == 3
    assert cleaned[0]["activity_type"] == "cycling"
    assert cleaned[1]["duration_minutes"] == 45