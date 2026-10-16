import datetime as dt
import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from coach import training_log
from coach.models import PlannedExercise, PlannedSession
from sync.models import Activity

TODAY = dt.date(2026, 10, 16)   # a Friday
GARMIN_PLACEHOLDER = [{"name": "Unknown", "reps": None, "weight_kg": None}]


def _act(day, kind="running", minutes=60, gid=None, **kw):
    return Activity.objects.create(
        garmin_id=gid or f"{day}-{kind}-{minutes}", activity_type=kind, duration_seconds=minutes * 60,
        start_time=timezone.make_aware(dt.datetime.combine(day, dt.time(10)), dt.timezone.utc), **kw)


def _plan(day, kind="gym_legs", exercises=(), **kw):
    p = PlannedSession.objects.create(date=day, activity_type=kind, title=kw.pop("title", kind), **kw)
    for i, (name, sets, reps, kg) in enumerate(exercises):
        PlannedExercise.objects.create(session=p, order=i, name=name, sets=sets, reps=reps, weight_kg=kg)
    return p


# --- one gym session, not two -------------------------------------------------------

@pytest.mark.django_db
def test_garmin_strength_plus_edited_gym_session_is_one_entry_with_calendar_exercises():
    day = TODAY - dt.timedelta(days=2)
    _act(day, "strength_training", 35, exercise_sets=GARMIN_PLACEHOLDER)
    _plan(day, "gym_upper", [("Chest dumbbell press", 3, 10, 18.0)], created_by="ai",
          prescribed={"exercises": [{"name": "Chest dumbbell press", "sets": 3, "reps": 10, "weight_kg": 16.0}]})

    log = training_log.recent_log(today=TODAY)
    gym = [e for e in log if e["group"] == "gym"]
    assert len(gym) == 1
    assert gym[0]["status"] == "done"
    assert gym[0]["minutes"] == 35
    assert gym[0]["exercises"] == ["Chest dumbbell press 3x10 @18kg"]
    assert gym[0]["exercises_source"] == "planned"
    assert gym[0]["prescribed"] == ["Chest dumbbell press 3x10 @16kg"]


@pytest.mark.django_db
def test_real_garmin_sets_win_over_the_calendar():
    day = TODAY - dt.timedelta(days=1)
    _act(day, "strength_training", exercise_sets=[{"name": "Back Squat", "reps": 6, "weight_kg": 80.0}] * 3)
    _plan(day, "gym_legs", [("Leg press", 3, 10, 100.0)])
    e = training_log.recent_log(today=TODAY)[0]
    assert e["exercises_source"] == "garmin"
    assert e["exercises"] == ["Back Squat 3x6 @80kg"]


def test_garmin_placeholder_set_is_not_a_record():
    assert not training_log._garmin_sets_usable(GARMIN_PLACEHOLDER)
    assert training_log._garmin_sets_usable([{"name": "Deadlift", "reps": 5, "weight_kg": None}])


# --- plan vs done -------------------------------------------------------------------

@pytest.mark.django_db
def test_planned_run_done_carries_the_plan():
    day = TODAY - dt.timedelta(days=3)
    _act(day, "running", 52, distance_meters=10000, elevation_gain_m=420.4,
         hr_zone_1_seconds=600, hr_zone_2_seconds=1800, hr_zone_4_seconds=600)
    _plan(day, "running", title="Easy hilly run", duration_minutes=60, intensity="easy")
    e = training_log.recent_log(today=TODAY)[0]
    assert e["status"] == "done"
    assert e["planned"] == {"title": "Easy hilly run", "activity_type": "running", "minutes": 60, "intensity": "easy"}
    assert e["pace"] == "5:12/km"
    assert e["elev_gain_m"] == 420
    assert (e["easy_min"], e["hard_min"]) == (40, 10)


@pytest.mark.django_db
def test_statuses_for_plans_without_activity():
    _plan(TODAY - dt.timedelta(days=4), "cycling", title="Skipped ride")
    _plan(TODAY - dt.timedelta(days=5), "gym_legs", [("Squat", 3, 5, 90.0)], prescribed={"exercises": []})
    _plan(TODAY - dt.timedelta(days=6), "running", completed=True, duration_minutes=40)
    _plan(TODAY + dt.timedelta(days=1), "running")                     # future: calendar, not log
    _act(TODAY - dt.timedelta(days=2), "inline_skating", 90)

    by_type = {e["type"]: e for e in training_log.recent_log(today=TODAY)}
    assert by_type["cycling"]["status"] == "missed"
    assert by_type["gym_legs"]["status"] == "done_manual"
    assert by_type["gym_legs"]["exercises"] == ["Squat 3x5 @90kg"]
    assert by_type["running"]["status"] == "done_manual" and by_type["running"]["minutes"] == 40
    assert by_type["inline_skating"]["status"] == "unplanned"
    assert len(by_type) == 4


@pytest.mark.django_db
def test_weekly_summary_and_baseline():
    monday = TODAY - dt.timedelta(days=TODAY.weekday())
    for w in range(1, 5):                                   # 4 complete weeks: 2 x 60 min running
        _act(monday - dt.timedelta(weeks=w), "running", 60, gid=f"a{w}", elevation_gain_m=300)
        _act(monday - dt.timedelta(weeks=w) + dt.timedelta(days=2), "running", 60, gid=f"b{w}")
    _act(monday, "road_biking", 120, distance_meters=50000)

    weeks = training_log.weekly_summary(weeks=5, today=TODAY)
    assert [w["partial"] for w in weeks] == [False, False, False, False, True]
    assert weeks[0]["groups"]["running"] == {"sessions": 2, "minutes": 120, "elev_gain_m": 300, "longest_min": 60}
    assert weeks[-1]["groups"]["cycling"]["km"] == 50.0
    assert training_log.baseline_minutes(today=TODAY) == {"running": 120}


@pytest.mark.django_db
def test_baseline_needs_two_weeks_of_data():
    _act(TODAY - dt.timedelta(days=10), "running", 60)
    assert training_log.baseline_minutes(today=TODAY) == {}


@pytest.mark.django_db
def test_exercise_history_follows_one_lift():
    for i, kg in enumerate((60, 65, 70)):
        _plan(TODAY - dt.timedelta(days=14 - i * 4), "gym_legs",
              [("Romanian deadlift", 3, 8, kg), ("Plank", 3, 1, None)], completed=True)
    rows = training_log.exercise_history("romanian", today=TODAY)
    assert [r["done"] for r in rows] == [["Romanian deadlift 3x8 @60kg"], ["Romanian deadlift 3x8 @65kg"],
                                         ["Romanian deadlift 3x8 @70kg"]]


def test_group_of_activity_maps_garmin_types():
    assert training_log.group_of_activity("treadmill_running") == "running"
    assert training_log.group_of_activity("indoor_cycling") == "cycling"
    assert training_log.group_of_activity("road_biking") == "cycling"
    assert training_log.group_of_activity("strength_training") == "gym"
    assert training_log.group_of_activity("inline_skating") == "skating"
    assert training_log.group_of_activity("tennis_v2") == "tennis"
    assert training_log.group_of_activity("backcountry_skiing") == "skiing"
    assert training_log.group_of_activity("lap_swimming") == "other"


# --- the calendar keeps the coach's version ------------------------------------------

@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


def _save(client, payload):
    return client.post(reverse("save_planned_session"), data=json.dumps(payload), content_type="application/json")


def test_first_edit_of_a_coach_session_saves_the_prescription(client, user):
    client.force_login(user)
    p = _plan(TODAY, "gym_upper", [("Shoulder press", 3, 10, 15.0)], created_by="ai", duration_minutes=45)
    edit = {"id": p.id, "date": TODAY.isoformat(), "activity_type": "gym_upper", "title": "Upper",
            "exercises": [{"name": "Shoulder press", "sets": 3, "reps": 8, "weight_kg": 17.5}]}
    _save(client, edit)
    p.refresh_from_db()
    assert p.prescribed["duration_minutes"] == 45
    assert p.prescribed["exercises"][0]["weight_kg"] == 15.0
    assert p.exercises.get().weight_kg == 17.5

    _save(client, {**edit, "exercises": [{"name": "Shoulder press", "sets": 3, "reps": 8, "weight_kg": 20}]})
    p.refresh_from_db()
    assert p.prescribed["exercises"][0]["weight_kg"] == 15.0          # second edit keeps the original


def test_own_sessions_get_no_prescription(client, user):
    client.force_login(user)
    p = _plan(TODAY, "gym_legs", created_by="human")
    _save(client, {"id": p.id, "date": TODAY.isoformat(), "activity_type": "gym_legs", "exercises": []})
    p.refresh_from_db()
    assert p.prescribed is None


# --- what the agent gets ----------------------------------------------------------

@pytest.mark.django_db
def test_context_has_the_log_and_weekly_summary_not_recent_activities():
    from coach.context import build_context
    _act(dt.date.today() - dt.timedelta(days=1), "running", 45)
    ctx = build_context()
    assert "recent_activities" not in ctx
    assert ctx["training_log"][0]["group"] == "running"
    assert len(ctx["weekly_summary"]) == 8 and ctx["weekly_summary"][-1]["partial"]


def test_get_training_history_registered_in_all_three_places():
    from coach.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
    assert "get_training_history" in TOOL_FUNCTIONS
    schema = next(d for d in TOOL_DEFINITIONS if d["name"] == "get_training_history")
    assert schema["input_schema"]["required"] == []
    assert set(schema["input_schema"]["properties"]) == {"group", "exercise", "weeks"}


@pytest.mark.django_db
def test_get_training_history_tool_returns_a_lifts_progression():
    from coach.tools import execute_tool
    _plan(dt.date.today() - dt.timedelta(days=3), "gym_legs", [("Back squat", 4, 6, 80.0)], completed=True)
    out = execute_tool("get_training_history", {"exercise": "squat"})
    assert json.loads(out)[0]["done"] == ["Back squat 4x6 @80kg"]
    assert "No running" in execute_tool("get_training_history", {"group": "running", "weeks": 99})


@pytest.mark.django_db
def test_check_training_week_warns_on_a_jump_over_done_volume():
    from coach.tools import execute_tool
    today = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    for w in range(1, 5):
        _act(monday - dt.timedelta(weeks=w), "running", 60, gid=f"r{w}")
    nxt = monday + dt.timedelta(weeks=1)
    week = [{"id": "running/easy-long", "start": f"{nxt + dt.timedelta(days=d)}T09:00", "minutes": 50}
            for d in (0, 3)]
    assert "progression" in execute_tool("check_training_week", {"sessions": week})
    assert "progression" not in execute_tool("check_training_week", {"sessions": week[:1]})
