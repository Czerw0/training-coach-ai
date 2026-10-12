import datetime as dt
import json
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from coach.context import _summarise_weather, build_context
from sync.models import UserProfile, WeatherHourly, WeatherLocation
from sync.weather import fetch_forecast

ZONES = [{"zone": f"Z{i + 1}", "min_bpm": lo, "max_bpm": hi}
         for i, (lo, hi) in enumerate([(0, 150), (151, 165), (166, 179), (180, 195), (196, None)])]


@pytest.fixture
def client_in(client, db):
    client.force_login(User.objects.create_user("u", password="pw12345"))
    return client


def post(client, name, body):
    return client.post(reverse(name), data=json.dumps(body), content_type="application/json")


def test_migration_seeds_warsaw_active_and_innsbruck(db):
    names = {l.name: l.is_active for l in WeatherLocation.objects.all()}
    assert names == {"Warsaw": True, "Innsbruck": False}


def test_settings_page_requires_login(client):
    assert client.get(reverse("settings_page")).status_code == 302


def test_save_profile_writes_fields_zones_and_days(client_in):
    resp = post(client_in, "save_profile", {"ftp_watts": 255, "max_hr": 200, "instruction_days": [6, 0, 0],
                                             "hr_zones": ZONES, "athlete_notes": "notes"})
    assert resp.json()["ok"]
    p = UserProfile.objects.get(pk=1)
    assert (p.ftp_watts, p.max_hr, p.instruction_days, p.athlete_notes) == (255, 200, [0, 6], "notes")
    assert p.hr_zones[4]["max_bpm"] is None


def test_save_profile_rejects_out_of_range_and_overlapping_zones(client_in):
    assert post(client_in, "save_profile", {"max_hr": 400}).status_code == 400
    bad = [dict(z) for z in ZONES]
    bad[1]["min_bpm"] = 140
    resp = post(client_in, "save_profile", {"hr_zones": bad})
    assert resp.status_code == 400 and "overlap" in resp.json()["error"]
    assert post(client_in, "save_profile", {"instruction_days": [7]}).status_code == 400


def test_activate_location_switches_and_fetches_when_no_forecast(client_in):
    innsbruck = WeatherLocation.objects.get(name="Innsbruck")
    with patch("coach.settings_views.fetch_forecast") as fetch:
        resp = post(client_in, "activate_location", {"id": innsbruck.id})
    assert resp.json()["ok"]
    fetch.assert_called_once()
    assert WeatherLocation.active().name == "Innsbruck"
    assert WeatherLocation.objects.filter(is_active=True).count() == 1


def test_cannot_delete_active_location(client_in):
    warsaw = WeatherLocation.objects.get(name="Warsaw")
    assert post(client_in, "delete_location", {"id": warsaw.id}).status_code == 400
    innsbruck = WeatherLocation.objects.get(name="Innsbruck")
    assert post(client_in, "delete_location", {"id": innsbruck.id}).json()["ok"]


def test_add_location_rejects_unknown_timezone(client_in):
    resp = post(client_in, "add_location", {"name": "X", "latitude": 1, "longitude": 1, "timezone": "Mars/Base"})
    assert resp.status_code == 400


def test_fetch_forecast_stores_local_times_per_location(db):
    loc = WeatherLocation.objects.get(name="Innsbruck")
    payload = {"hourly": {k: [v, v] for k, v in {
        "temperature_2m": 5.0, "relative_humidity_2m": 80, "precipitation_probability": 10, "precipitation": 0.0,
        "cloud_cover": 50, "wind_speed_10m": 9.0, "weather_code": 2, "uv_index": 1.0, "is_day": 1}.items()}}
    future = timezone.now().astimezone(ZoneInfo("Europe/Vienna")) + dt.timedelta(days=1)
    payload["hourly"]["time"] = [future.strftime("%Y-%m-%dT08:00"), future.strftime("%Y-%m-%dT09:00")]
    resp = MagicMock(); resp.json.return_value = payload
    with patch("sync.weather.requests.get", return_value=resp):
        assert fetch_forecast(loc) == 2
    h = WeatherHourly.objects.filter(location=loc).order_by("datetime").first()
    assert h.datetime.astimezone(ZoneInfo("Europe/Vienna")).hour == 8


def test_weather_summary_buckets_in_location_time():
    # 06:30 UTC is 08:30 in Vienna (summer) -> morning, not night
    hour = {"datetime": dt.datetime(2026, 7, 1, 6, 30, tzinfo=dt.timezone.utc), "temp": 20,
            "precipitation_probability": 0, "wind_speed": 5, "weather_code": 0}
    assert "morning (06-12)" in _summarise_weather([hour], ZoneInfo("Europe/Vienna"))["2026-07-01"]


def test_context_has_location_and_profile_instruction_days(db):
    UserProfile.objects.create(pk=1, instruction_days=[dt.date.today().weekday()])
    ctx = build_context()
    assert ctx["location"] == "Warsaw"
    assert ctx["next_14_days"][0]["usual_instruction_day"] is True
    assert ctx["next_14_days"][1]["usual_instruction_day"] is False
