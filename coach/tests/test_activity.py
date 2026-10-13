import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from coach.activity import sport_of
from coach.models import PlannedSession
from sync.models import Activity


def _act(days_ago, kind="indoor_cycling", power=200, minutes=60, **kw):
    when = timezone.now() - dt.timedelta(days=days_ago)
    return Activity.objects.create(garmin_id=f"{kind}-{days_ago}-{power}", activity_type=kind, activity_name=f"{kind} {days_ago}",
                                   start_time=when, duration_seconds=minutes * 60, training_load=minutes, avg_power=power, **kw)


@pytest.fixture
def client_in(client, db):
    client.force_login(User.objects.create_user("a", password="pw12345"))
    return client


def test_sport_of():
    assert [sport_of(t) for t in ["road_biking", "treadmill_running", "strength_training", "lap_swimming", "inline_skating"]] == \
        ["cycling", "running", "strength", "swimming", "other"]


def test_activity_pages_require_login(client, db):
    a = _act(1)
    assert client.get(reverse("activity_page", args=[a.id])).status_code == 302
    assert client.get(reverse("activities_data")).status_code == 302


def test_activity_page_404(client_in):
    assert client_in.get(reverse("activity_page", args=[999])).status_code == 404
    assert client_in.get(reverse("activity_data", args=[999])).status_code == 404


def test_activity_data_compares_with_previous_90_days(client_in):
    for d, p in [(10, 200), (20, 200), (30, 200), (200, 50)]:   # the 200-day-old one is outside the window
        _act(d, power=p)
    a = _act(1, power=220)
    PlannedSession.objects.create(date=a.start_time.date(), activity_type="cycling", title="Sweetspot")
    data = client_in.get(reverse("activity_data", args=[a.id])).json()
    power = next(m for m in data["metrics"] if m["key"] == "avg_power")
    assert power["avg"] == 200 and power["delta_pct"] == 10
    assert data["compared_with"] == 3
    assert data["plan"]["title"] == "Sweetspot"
    assert data["prev"]["id"] and data["next"] is None
    assert not any(m["key"] == "avg_running_cadence" for m in data["metrics"])   # sport-specific only


def test_running_pace_is_computed(client_in):
    a = _act(1, kind="running", minutes=50, distance_meters=10000)
    pace = next(m for m in client_in.get(reverse("activity_data", args=[a.id])).json()["metrics"] if m["key"] == "pace")
    assert pace["value"] == 300   # 5:00 per km


def test_activities_list_filters_and_searches(client_in):
    _act(1, kind="road_biking"); _act(2, kind="running"); _act(3, kind="strength_training")
    assert client_in.get(reverse("activities_data") + "?sport=running").json()["total"] == 1
    assert client_in.get(reverse("activities_data") + "?sport=other").json()["total"] == 0
    assert client_in.get(reverse("activities_data") + "?q=strength").json()["total"] == 1
    assert client_in.get(reverse("activities_data")).json()["total"] == 3
