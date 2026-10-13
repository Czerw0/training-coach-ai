import datetime as dt
import json

import pytest
from django.contrib.auth.models import User

from coach import athlete_rules
from coach.context import build_context
from coach.dashboard import build_insights
from coach.models import PlannedSession, ProfileChange
from coach.tools import check_training_week, create_planned_session
from sync.models import IndoorCyclingWorkout, UserProfile


def _profile(**rules):
    return UserProfile.objects.update_or_create(pk=1, defaults={"rules": rules})[0]


def _next(weekday_name):
    today = dt.date.today()
    for i in range(1, 8):
        d = today + dt.timedelta(days=i)
        if d.strftime("%A") == weekday_name:
            return d.isoformat()


def test_rules_validate_groups_and_ranges():
    with pytest.raises(Exception):
        athlete_rules.AthleteRules(weekly_caps={"running": 20})
    with pytest.raises(Exception):
        athlete_rules.AthleteRules(unavailable=["golf"])
    r = athlete_rules.AthleteRules(focus_areas=[" glutes ", "glutes", ""], unavailable=["gym", "gym"])
    assert r.focus_areas == ["glutes"] and r.unavailable == ["gym"]


@pytest.mark.django_db
def test_bad_stored_json_means_no_rules_not_a_crash():
    _profile(weekly_caps={"running": "lots"})
    assert athlete_rules.load().weekly_caps == {}


@pytest.mark.django_db
def test_create_planned_session_refuses_unavailable_activity():
    _profile(unavailable=["cycling", "gym"])
    date = _next("Friday")
    out = create_planned_session(date=date, weekday="Friday", activity_type="cycling")
    assert out.startswith("Not written") and not PlannedSession.objects.exists()
    assert create_planned_session(date=date, weekday="Friday", activity_type="gym_legs").startswith("Not written")
    assert create_planned_session(date=date, weekday="Friday", activity_type="running").startswith("Planned")


@pytest.mark.django_db
def test_week_checker_uses_the_athletes_caps_and_unavailable():
    _profile(weekly_caps={"running": 1}, unavailable=["cycling"])
    week = [{"id": "running/easy-long", "start": "2026-08-10T18:00"},
            {"id": "running/easy-long", "start": "2026-08-13T18:00"},
            {"id": "cycling/endurance", "start": "2026-08-14T18:00"}]
    out = check_training_week(week)
    assert "weekly-cap" in out and "max 1 per week" in out
    assert "unavailable" in out
    _profile(weekly_caps={"running": 3})
    assert "weekly-cap" not in check_training_week(week[:2])


@pytest.mark.django_db
def test_context_carries_rules_and_hides_the_trainer_catalog_when_no_bike():
    IndoorCyclingWorkout.objects.create(name="Z2", category="endurance", duration_min=60, intensity_factor=0.65, tss=45)
    _profile(unavailable=["cycling"], focus_areas=["balance"])
    ctx = build_context()
    assert ctx["user_profile"]["athlete_rules"]["unavailable"] == ["cycling"]
    assert ctx["indoor_cycling_workouts"] == []
    _profile()
    assert len(build_context()["indoor_cycling_workouts"]) == 1


@pytest.mark.django_db
def test_settings_saves_rules_and_logs_the_change(client):
    client.force_login(User.objects.create_user("r", password="pw12345"))
    body = {"primary_sport": "running", "rules": {"weekly_caps": {"running": 2}, "unavailable": ["cycling"],
                                                  "focus_areas": ["glutes"], "light_day_label": "Teaching"}}
    r = client.post("/settings/profile/", data=json.dumps(body), content_type="application/json").json()
    assert r["ok"]
    assert UserProfile.objects.get(pk=1).rules["unavailable"] == ["cycling"]
    assert ProfileChange.objects.filter(field="rules").exists()
    data = client.get("/settings/data/").json()
    assert data["profile"]["rules"]["light_day_label"] == "Teaching" and "mountaineering" in data["rule_groups"]
    bad = {**body, "rules": {"weekly_caps": {"golf": 1}}}
    assert client.post("/settings/profile/", data=json.dumps(bad), content_type="application/json").status_code == 400


@pytest.mark.django_db
def test_today_run_warning_follows_the_cap():
    today = dt.date.today()
    week = [{"date": today.isoformat(), "done": ["running"], "planned": []},
            {"date": (today - dt.timedelta(days=1)).isoformat(), "done": ["trail_running"], "planned": []}]
    _profile(weekly_caps={"running": 2})
    assert not any("runs this week" in i["title"] for i in build_insights(today, None, (None, None), None, week))
    _profile(weekly_caps={"running": 1})
    hit = [i for i in build_insights(today, None, (None, None), None, week) if "runs this week" in i["title"]]
    assert hit and "allow 1 run a week" in hit[0]["text"]
    _profile()
    assert not any("runs this week" in i["title"] for i in build_insights(today, None, (None, None), None, week))
