"""Open-Meteo forecast + geocoding, shared by `manage.py sync_weather` and the
settings page. Free API, no key."""
import datetime as dt
from zoneinfo import ZoneInfo

import requests
from django.utils import timezone

from sync.models import WeatherHourly

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
HOURLY = ["temperature_2m", "relative_humidity_2m", "precipitation_probability", "precipitation",
          "cloud_cover", "wind_speed_10m", "weather_code", "uv_index", "is_day"]


def fetch_forecast(location, days=7):
    """Fetch and store hourly forecast for one location. Returns rows saved.
    Open-Meteo returns local wall-clock times for the requested timezone, so
    they are made aware in that zone (not UTC) before saving."""
    resp = requests.get(FORECAST_URL, timeout=20, params={
        "latitude": location.latitude, "longitude": location.longitude,
        "hourly": HOURLY, "timezone": location.timezone, "forecast_days": days,
    })
    resp.raise_for_status()
    h = resp.json()["hourly"]
    tz = ZoneInfo(location.timezone)
    saved = 0
    for i, stamp in enumerate(h["time"]):
        when = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M").replace(tzinfo=tz)
        WeatherHourly.objects.update_or_create(location=location, datetime=when, defaults={
            "temp": h["temperature_2m"][i], "humidity": h["relative_humidity_2m"][i],
            "precipitation_probability": h["precipitation_probability"][i], "precipitation": h["precipitation"][i],
            "cloud_cover": h["cloud_cover"][i], "wind_speed": h["wind_speed_10m"][i],
            "weather_code": h["weather_code"][i], "uv_index": h["uv_index"][i], "is_day": bool(h["is_day"][i]),
        })
        saved += 1
    WeatherHourly.objects.filter(location=location, datetime__lt=timezone.now() - dt.timedelta(days=2)).delete()
    return saved


def geocode(query, count=6):
    """City name -> [{name, country, admin, latitude, longitude, timezone}]."""
    resp = requests.get(GEOCODE_URL, timeout=10, params={"name": query, "count": count, "language": "en", "format": "json"})
    resp.raise_for_status()
    return [{
        "name": r["name"], "country": r.get("country", ""), "admin": r.get("admin1", ""),
        "latitude": round(r["latitude"], 4), "longitude": round(r["longitude"], 4),
        "timezone": r.get("timezone") or "UTC",
    } for r in resp.json().get("results") or []]
