import datetime as dt

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from coach.stats import correlations, fitness_series, records
from sync.models import Activity

D = dt.date(2026, 10, 13)


def _act(day, load, minutes=60, kind="cycling"):
    return Activity.objects.create(
        garmin_id=f"{day}-{kind}-{load}", activity_type=kind, training_load=load, duration_seconds=minutes * 60,
        start_time=timezone.make_aware(dt.datetime.combine(day, dt.time(17))),
    )


@pytest.mark.django_db
def test_fitness_series_constant_load_converges():
    for back in range(200):
        _act(D - dt.timedelta(days=back), 100)
    s = fitness_series(D - dt.timedelta(days=6), D)
    assert len(s) == 7
    last = s[-1]
    assert 95 < last["atl"] <= 100          # 7-day constant converges fast
    assert last["ctl"] > 80                 # 42-day converges slower
    assert last["tsb"] == round(last["ctl"] - last["atl"], 1)


@pytest.mark.django_db
def test_correlations_stay_quiet_without_enough_data():
    _act(D, 50)
    assert correlations(D - dt.timedelta(days=27), D) == []


def test_records_picks_longest_and_biggest_week():
    when = timezone.make_aware(dt.datetime(2026, 10, 1, 17))
    rows = [{"start_time": when, "activity_name": "Long ride", "activity_type": "cycling", "duration_seconds": 3 * 3600,
             "distance_meters": 80000, "training_load": 200}]
    weeks = [{"week_start": "2026-09-28", "hours": 7.5}, {"week_start": "2026-10-05", "hours": 4.0}]
    out = {r["label"]: r for r in records(rows, weeks)}
    assert out["Longest session"]["value"] == "180 min"
    assert out["Longest distance"]["value"] == "80.0 km"
    assert out["Biggest week"]["value"] == "7.5 h"


@pytest.mark.django_db
def test_stats_data_period_param_and_unknown_period(client):
    client.force_login(User.objects.create_user("s", password="pw12345"))
    data = client.get(reverse("stats_data") + "?days=28").json()
    assert data["period"]["days"] == 28
    assert len(data["recovery"]) == 28
    assert client.get(reverse("stats_data") + "?days=999").json()["period"]["days"] == 84
    assert client.get(reverse("stats_data") + "?days=abc").json()["period"]["days"] == 84
