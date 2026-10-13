import datetime as dt
import json
import pathlib
import re
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse

from coach import sync_schedule
from coach.models import DailyFeeling, Injury, SyncStatus

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _cron_hours(workflow):
    text = (ROOT / ".github" / "workflows" / workflow).read_text(encoding="utf-8")
    minute, hours = re.search(r"cron:\s*'(\S+) (\S+) \* \* \*'", text).groups()
    assert minute == "0"
    return tuple(int(h) for h in hours.split(","))


def test_schedule_matches_workflow_crons():
    assert sync_schedule.GARMIN_HOURS_UTC == _cron_hours("garmin_sync.yml")
    assert sync_schedule.WEATHER_HOURS_UTC == _cron_hours("weather_sync.yml")


def test_next_and_previous_run_wrap_across_midnight():
    utc = dt.timezone.utc
    late = dt.datetime(2026, 10, 13, 22, 30, tzinfo=utc)
    assert sync_schedule.next_run(sync_schedule.GARMIN_HOURS_UTC, late) == dt.datetime(2026, 10, 14, 4, tzinfo=utc)
    assert sync_schedule.previous_run(sync_schedule.GARMIN_HOURS_UTC, late) == dt.datetime(2026, 10, 13, 21, tzinfo=utc)
    early = dt.datetime(2026, 10, 13, 2, tzinfo=utc)
    assert sync_schedule.previous_run(sync_schedule.GARMIN_HOURS_UTC, early) == dt.datetime(2026, 10, 12, 21, tzinfo=utc)


@pytest.mark.django_db
def test_sync_garmin_records_done_and_error():
    with patch("sync.management.commands.sync_garmin.Command._run"):
        call_command("sync_garmin")
    assert SyncStatus.objects.get(pk=1).state == "done"
    with patch("sync.management.commands.sync_garmin.Command._run", side_effect=RuntimeError("429 rate limited")):
        with pytest.raises(RuntimeError):
            call_command("sync_garmin")
    s = SyncStatus.objects.get(pk=1)
    assert s.state == "error" and "429" in s.message


@pytest.fixture
def client_in(client, db):
    client.force_login(User.objects.create_user("t", password="pw12345"))
    return client


def test_log_feel_saves_soreness_and_parts(client_in):
    r = client_in.post(reverse("log_feel"), json.dumps({"muscle_soreness": 6, "parts": ["Hamstrings", "Glutes"]}),
                       content_type="application/json").json()
    assert r["ok"] and r["feel"]["soreness"] == 6
    f = DailyFeeling.objects.get(date=dt.date.today())
    assert (f.muscle_soreness, f.muscle_sore) == (6, "Hamstrings, Glutes")


@pytest.mark.parametrize("body", [{"muscle_soreness": 0}, {"muscle_soreness": 11}, {"muscle_soreness": 5, "parts": ["Elbows"]}, {}])
def test_log_feel_rejects_bad_input(client_in, body):
    assert client_in.post(reverse("log_feel"), json.dumps(body), content_type="application/json").status_code == 400
    assert not DailyFeeling.objects.exists()


def test_today_data_has_sync_feel_and_injuries(client_in):
    Injury.objects.create(body_part="left knee", severity="minor", date_started=dt.date.today() - dt.timedelta(days=10))
    Injury.objects.create(body_part="wrist", severity="minor", date_started=dt.date(2026, 1, 1), date_resolved=dt.date(2026, 2, 1))
    data = client_in.get(reverse("today_data")).json()
    assert data["sync"]["next"] and data["sync"]["next_weather"]
    assert [i["body_part"] for i in data["injuries"]] == ["left knee"]
    assert data["injuries"][0]["since_days"] == 10
    assert "Hamstrings" in data["sore_parts"]
