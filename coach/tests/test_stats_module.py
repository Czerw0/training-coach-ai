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


@pytest.mark.django_db
def test_feel_stats_counts_parts_and_averages():
    from coach.models import DailyFeeling
    from coach.stats import feel_stats
    for i, (s, parts) in enumerate([(6, "Hamstrings, Glutes"), (4, "hamstrings"), (2, None)]):
        DailyFeeling.objects.create(date=D - dt.timedelta(days=i), muscle_soreness=s, energy_level=7, muscle_sore=parts)
    out = feel_stats(D - dt.timedelta(days=27), D)
    assert out["days_logged"] == 3 and out["avg"]["soreness"] == 4.0
    assert out["parts"][0] == {"part": "Hamstrings", "n": 2}
    assert out["after_hard"] is None   # not enough data


@pytest.mark.django_db
def test_injury_list_keeps_last_12_months_and_open_ones():
    from coach.models import Injury
    from coach.stats import injury_list
    Injury.objects.create(body_part="left knee", date_started=D - dt.timedelta(days=400))                     # still open
    Injury.objects.create(body_part="wrist", date_started=D - dt.timedelta(days=60), date_resolved=D - dt.timedelta(days=30))
    Injury.objects.create(body_part="back", date_started=D - dt.timedelta(days=500), date_resolved=D - dt.timedelta(days=450))
    out = {i["body_part"]: i for i in injury_list(D)}
    assert set(out) == {"Left Knee", "Wrist"}
    assert out["Wrist"]["days"] == 30 and out["Left Knee"]["end"] is None
