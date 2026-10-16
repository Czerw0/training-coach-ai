import datetime as dt
import json
from types import SimpleNamespace
from unittest import mock

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from coach import insights
from coach.models import AiInsight, ApiUsage, Injury
from sync.models import Activity

ITEMS = [{"title": f"Point {i}", "text": f"Evidence {i}."} for i in range(6)]


def _response(items=ITEMS, stop="end_turn"):
    return SimpleNamespace(
        stop_reason=stop,
        content=[SimpleNamespace(type="text", text=json.dumps({"insights": items}))],
        usage=SimpleNamespace(input_tokens=1500, output_tokens=400, cache_creation_input_tokens=0, cache_read_input_tokens=0),
    )


@pytest.fixture
def api():
    with mock.patch.object(insights.client.messages, "create", return_value=_response()) as m:
        yield m


@pytest.fixture
def user_client(client):
    client.force_login(User.objects.create_user("i", password="pw12345"))
    return client


@pytest.fixture
def activity():
    return Activity.objects.create(garmin_id="g1", activity_type="cycling", activity_name="Evening ride",
                                   duration_seconds=3600, training_load=120, avg_hr=140,
                                   start_time=timezone.now() - dt.timedelta(hours=3))


@pytest.mark.django_db
def test_generates_once_then_serves_from_db(user_client, api, activity):
    url = f"/insights/activity/{activity.id}/"
    first = user_client.post(url).json()
    assert first["ok"] and not first["cached"] and len(first["items"]) == 6
    second = user_client.post(url).json()
    assert second["cached"] and second["items"] == first["items"]
    assert api.call_count == 1
    assert user_client.get(url).json()["items"] == first["items"]


@pytest.mark.django_db
def test_request_shape_no_tools_no_thinking_structured_output(user_client, api, activity):
    user_client.post(f"/insights/activity/{activity.id}/")
    kw = api.call_args.kwargs
    assert kw["thinking"] == {"type": "disabled"}
    assert "tools" not in kw
    assert kw["output_config"]["format"]["type"] == "json_schema"
    assert "Write 5 to 8 insights" in kw["messages"][0]["content"]


@pytest.mark.django_db
def test_logs_api_usage_under_insights_config(user_client, api, activity):
    user_client.post(f"/insights/activity/{activity.id}/")
    row = ApiUsage.objects.get()
    assert row.config_version == "insights-v1" and row.input_tokens == 1500 and row.cost_usd > 0
    assert AiInsight.objects.get().cost_usd == pytest.approx(row.cost_usd)


@pytest.mark.django_db
def test_refresh_is_rate_limited(user_client, api, activity):
    url = f"/insights/activity/{activity.id}/"
    user_client.post(url)
    r = user_client.post(url + "?refresh=1")
    assert r.status_code == 429 and r.json()["items"]
    assert api.call_count == 1
    AiInsight.objects.update(created_at=timezone.now() - dt.timedelta(minutes=11))
    assert user_client.post(url + "?refresh=1").json()["cached"] is False
    assert api.call_count == 2 and AiInsight.objects.count() == 1


@pytest.mark.django_db
def test_invalid_model_output_is_not_saved_but_still_logged(user_client, activity):
    bad = _response(items=[{"title": "", "text": "x"}])
    with mock.patch.object(insights.client.messages, "create", return_value=bad):
        r = user_client.post(f"/insights/activity/{activity.id}/")
    assert r.status_code == 502
    assert not AiInsight.objects.exists() and ApiUsage.objects.count() == 1


@pytest.mark.django_db
def test_truncated_output_is_rejected(user_client, activity):
    with mock.patch.object(insights.client.messages, "create", return_value=_response(stop="max_tokens")):
        assert user_client.post(f"/insights/activity/{activity.id}/").status_code == 502


@pytest.mark.django_db
def test_items_capped_to_scope_maximum(user_client, activity):
    with mock.patch.object(insights.client.messages, "create", return_value=_response(items=ITEMS)):
        d = user_client.post("/insights/hrv/x/").json()
    assert len(d["items"]) == 3


@pytest.mark.django_db
def test_tiles_key_by_today_and_unknown_scope_404(user_client, api):
    user_client.post("/insights/sleep/whatever/")
    assert AiInsight.objects.get().key == dt.date.today().isoformat()
    assert user_client.post("/insights/weather/today/").status_code == 404
    assert user_client.post("/insights/activity/999999/").status_code == 404


@pytest.mark.django_db
def test_injuries_payload_includes_every_injury_and_names_for_hiding(user_client, api):
    Injury.objects.create(body_part="left knee", date_started=dt.date.today() - dt.timedelta(days=5))
    d = user_client.post("/insights/injuries/today/").json()
    payload = api.call_args.kwargs["messages"][0]["content"]
    assert "left knee" in payload            # the agent side always sees every injury
    assert list(d["injury_names"].values()) == ["Left Knee"]


@pytest.mark.django_db
@pytest.mark.parametrize("scope", ["sleep", "hrv", "form", "injuries"])
def test_tile_payloads_build_on_empty_db(scope):
    out = insights.PAYLOADS[scope]("x", dt.date.today())
    json.dumps(out, default=str)


@pytest.mark.django_db
def test_requires_login(client, activity):
    assert client.post(f"/insights/activity/{activity.id}/").status_code == 302


@pytest.mark.django_db
def test_activity_list_marks_activities_with_insights(user_client, activity):
    AiInsight.objects.create(scope="activity", key=str(activity.id), items=ITEMS[:5])
    item = user_client.get("/activities/data/").json()["items"][0]
    assert item["has_insights"] is True


# --- v1.2: about today, with the notes from those days ---------------------------------

@pytest.mark.django_db
def test_sleep_payload_is_about_last_night_with_averages_as_baseline():
    from sync.models import SleepRecord
    today = dt.date.today()
    for i, score in enumerate([55, 80, 82, 78, 81, 79]):
        SleepRecord.objects.create(date=today - dt.timedelta(days=i), score=score, duration_hours=7.0)
    SleepRecord.objects.create(date=today - dt.timedelta(days=60), score=20, duration_hours=3.0)
    out = insights._sleep("x", today)
    assert out["data_age_days"] == 0
    assert out["focus"]["last_night"]["score"] == 55
    assert [n["score"] for n in out["focus"]["previous_3_nights"]] == [80, 82, 78]
    assert out["baseline"]["avg_30_nights"]["score"] == 75.8
    assert "20" not in json.dumps(out["baseline"])       # two months ago is outside every window


@pytest.mark.django_db
def test_stale_hrv_is_flagged():
    from sync.models import HRVRecord
    today = dt.date.today()
    HRVRecord.objects.create(date=today - dt.timedelta(days=3), hrv_rmssd=60)
    assert insights._hrv("x", today)["data_age_days"] == 3


@pytest.mark.django_db
def test_injuries_baseline_counts_old_injuries_without_dates():
    today = dt.date.today()
    Injury.objects.create(body_part="left knee", date_started=today - dt.timedelta(days=200),
                          date_resolved=today - dt.timedelta(days=150), description="old flare")
    out = insights._injuries("x", today)
    assert out["focus"]["active"] == []
    assert out["baseline"]["injuries_last_12_months_per_body_part"] == {"Left Knee": 1}
    assert "old flare" not in json.dumps(out)


@pytest.mark.django_db
def test_coach_notes_cover_the_last_three_days_only():
    from coach.models import CoachRecommendation, DailyFeeling
    today = dt.date.today()
    DailyFeeling.objects.create(date=today - dt.timedelta(days=1), energy_level=3, notes="wedding, two glasses of wine")
    DailyFeeling.objects.create(date=today - dt.timedelta(days=7), notes="old note")
    CoachRecommendation.objects.create(date=today, user_message="slept badly", recommendation="Easy day: Z1 spin.")
    notes = insights.coach_notes(insights._last_days(today))
    text = json.dumps(notes)
    assert "wedding" in text and "Easy day" in text
    assert "old note" not in text
    assert notes[0]["date"] == today.isoformat()


@pytest.mark.django_db
def test_tile_request_carries_coach_notes(user_client, api):
    from coach.models import DailyFeeling
    DailyFeeling.objects.create(date=dt.date.today(), notes="flight yesterday")
    user_client.post("/insights/sleep/today/")
    assert "flight yesterday" in api.call_args.kwargs["messages"][0]["content"]


@pytest.mark.django_db
def test_tile_from_an_older_prompt_is_regenerated(user_client, api):
    AiInsight.objects.create(scope="hrv", key=dt.date.today().isoformat(), items=ITEMS[:3], prompt_version="insights-v1.1")
    assert user_client.get("/insights/hrv/today/").json()["items"] is None
    user_client.post("/insights/hrv/today/")
    assert api.call_count == 1
    assert AiInsight.objects.get().prompt_version == insights.PROMPT_VERSION
