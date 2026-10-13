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
