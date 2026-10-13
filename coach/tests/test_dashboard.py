import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from coach import metrics
from coach.dashboard import build_insights
from coach.models import PlannedSession
from sync.models import Activity, HRVRecord

TODAY = dt.date(2026, 10, 13)


def _activity(day, load, kind="cycling", gid=None):
    return Activity.objects.create(
        garmin_id=gid or f"{day.isoformat()}-{kind}-{load}", activity_type=kind, training_load=load, duration_seconds=3600,
        start_time=timezone.make_aware(dt.datetime.combine(day, dt.time(17))),
    )


@pytest.mark.django_db
def test_acwr_uses_7_and_28_day_windows():
    for back in range(28):                       # 28 days x 10 load, today included
        _activity(TODAY - dt.timedelta(days=back), 10)
    _activity(TODAY - dt.timedelta(days=28), 1000)  # one day outside the chronic window
    acute, chronic, ratio = metrics.acwr(TODAY)
    assert (acute, chronic) == (70, 280)
    assert ratio == 1.0


def test_readiness_reweights_missing_inputs():
    score, parts = metrics.readiness(None, (None, None), 80, 1.0)
    assert set(parts) == {"sleep", "load"}
    assert score == round((80 * .35 + 100 * .25) / .60)


def test_readiness_high_load_is_penalised():
    _, parts = metrics.readiness(None, (None, None), None, 1.5)
    assert parts["load"] == 60


def test_readiness_label_thresholds():
    assert metrics.readiness_label(80)[1] == "good"
    assert metrics.readiness_label(60)[1] == "warn"
    assert metrics.readiness_label(40)[1] == "bad"
    assert metrics.readiness_label(None)[1] == "muted"


@pytest.mark.django_db
def test_insights_flag_more_than_one_run_a_week():
    week = [{"date": (TODAY + dt.timedelta(days=i)).isoformat(), "done": [], "planned": []} for i in range(-1, 6)]
    week[0]["done"] = ["running"]
    week[3]["planned"] = [{"type": "running", "title": "Tempo"}]
    titles = [i["title"] for i in build_insights(TODAY, None, (None, None), None, week)]
    assert "2 runs this week" in titles


@pytest.mark.django_db
def test_insights_count_a_completed_planned_run_once():
    week = [{"date": TODAY.isoformat(), "done": ["running"], "planned": [{"type": "running", "title": "Tempo"}]}]
    titles = [i["title"] for i in build_insights(TODAY, None, (None, None), None, week)]
    assert not any("runs this week" in t for t in titles)


@pytest.mark.django_db
def test_insights_flag_hrv_below_baseline():
    for back in range(1, 15):
        HRVRecord.objects.create(date=TODAY - dt.timedelta(days=back), hrv_rmssd=60 + (back % 2) * 4)
    baseline = metrics.hrv_baseline(TODAY)
    out = build_insights(TODAY, 40, baseline, 1.0, [])
    assert out[0]["level"] == "warn" and "below your normal range" in out[0]["title"]


@pytest.mark.django_db
def test_today_page_requires_login(client):
    resp = client.get(reverse("today_page"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_today_data_payload_shape(client):
    client.force_login(User.objects.create_user("a", password="pw12345"))
    today = dt.date.today()
    PlannedSession.objects.create(date=today, activity_type="running", title="Tempo", description="Purpose: test")
    _activity(today, 50, "running")
    data = client.get(reverse("today_data")).json()
    for key in ["readiness", "hrv", "sleep", "load", "today_sessions", "week", "latest_activity", "insights"]:
        assert key in data
    assert data["today_sessions"][0]["title"] == "Tempo"
    assert len(data["week"]) == 7
    assert len(data["load"]["weekly"]) == 8


def test_weather_parts_bucket_in_local_time_with_night_after_midnight():
    from zoneinfo import ZoneInfo
    from coach.dashboard import weather_parts
    tz = ZoneInfo("Europe/Vienna")
    def h(hour, day=13, code=2, temp=10):
        return {"datetime": dt.datetime(2026, 10, day, hour, tzinfo=tz), "temp": temp,
                "precipitation_probability": 10, "wind_speed": 5, "weather_code": code, "is_day": 6 <= hour < 19}
    rows = [h(9), h(10, code=61, temp=12), h(23, code=0), h(2, day=14, code=3, temp=4)]
    parts = weather_parts(rows, tz)
    assert [(p["part"], p["date"]) for p in parts] == [("Morning", "2026-10-13"), ("Night", "2026-10-13")]
    assert parts[0]["code"] == 61 and (parts[0]["t_min"], parts[0]["t_max"]) == (10, 12)
    assert parts[1]["is_day"] is False and parts[1]["t_min"] == 4
