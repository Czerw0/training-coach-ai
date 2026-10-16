import datetime as dt
import json

import pytest
from django.contrib.auth.models import User

from coach import markers
from coach.models import DailyFeeling, Illness, Injury
from coach.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS, execute_tool

TODAY = dt.date.today()


def d(n):
    return TODAY - dt.timedelta(days=n)


@pytest.fixture
def cl(client, db):
    client.force_login(User.objects.create_user("m", password="pw12345"))
    return client


def post(cl, url, body):
    return cl.post(url, data=json.dumps(body), content_type="application/json")


# --- reading ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_collect_marks_every_day_of_a_period_and_drinks():
    Injury.objects.create(body_part="left knee", date_started=d(5), date_resolved=d(3))
    Illness.objects.create(date_started=d(2), symptoms="cold")                      # still open
    DailyFeeling.objects.create(date=d(4), alcohol_drinks=3)
    DailyFeeling.objects.create(date=d(1), energy_level=5)                          # no drinks -> no dot
    out = markers.collect(d(10), TODAY + dt.timedelta(days=30))

    kinds = {day: [m["kind"] for m in items] for day, items in out["days"].items()}
    assert kinds[d(5).isoformat()] == ["injury"]
    assert kinds[d(4).isoformat()] == ["injury", "alcohol"]
    assert kinds[d(3).isoformat()] == ["injury"]
    assert [day for day, k in kinds.items() if "illness" in k] == [d(2).isoformat(), d(1).isoformat(), TODAY.isoformat()]
    assert out["alcohol"] == {d(4).isoformat(): 3}
    assert d(1).isoformat() not in out["alcohol"]


@pytest.mark.django_db
def test_markers_endpoint_validates_the_range(cl):
    assert cl.get("/calendar/markers/?start=2026-01-01&end=2026-02-01").json()["ok"]
    assert cl.get("/calendar/markers/?start=2026-01-01&end=2026-12-01").status_code == 400
    assert cl.get("/calendar/markers/?start=nope&end=2026-02-01").status_code == 400


def test_markers_need_login(client):
    assert client.get("/calendar/markers/?start=2026-01-01&end=2026-02-01").status_code == 302


# --- editing ---------------------------------------------------------------------------

def test_alcohol_set_edit_and_clear(cl):
    assert post(cl, "/calendar/marker/alcohol/", {"date": d(1).isoformat(), "drinks": 4}).json()["ok"]
    assert DailyFeeling.objects.get(date=d(1)).alcohol_drinks == 4
    post(cl, "/calendar/marker/alcohol/", {"date": d(1).isoformat(), "drinks": 2})
    assert DailyFeeling.objects.get(date=d(1)).alcohol_drinks == 2
    post(cl, "/calendar/marker/alcohol/", {"date": d(1).isoformat(), "drinks": 0})
    assert DailyFeeling.objects.get(date=d(1)).alcohol_drinks is None


def test_alcohol_rejects_future_and_silly_numbers(cl):
    assert post(cl, "/calendar/marker/alcohol/", {"date": (TODAY + dt.timedelta(days=1)).isoformat(), "drinks": 1}).status_code == 400
    assert post(cl, "/calendar/marker/alcohol/", {"date": TODAY.isoformat(), "drinks": 99}).status_code == 400
    assert not DailyFeeling.objects.exists()


def test_illness_create_edit_delete(cl):
    r = post(cl, "/calendar/marker/illness/", {"date_started": d(3).isoformat(), "symptoms": "flu", "systemic": True}).json()
    ill = Illness.objects.get(id=r["id"])
    assert ill.systemic and ill.date_resolved is None
    post(cl, "/calendar/marker/illness/", {"id": ill.id, "date_started": d(3).isoformat(), "date_resolved": d(1).isoformat(), "symptoms": "flu"})
    ill.refresh_from_db()
    assert ill.date_resolved == d(1) and not ill.systemic
    assert post(cl, "/calendar/marker/illness/delete/", {"id": ill.id}).json()["ok"]
    assert not Illness.objects.exists()


def test_period_end_before_start_is_rejected(cl):
    r = post(cl, "/calendar/marker/injury/", {"body_part": "ankle", "date_started": d(1).isoformat(), "date_resolved": d(5).isoformat()})
    assert r.status_code == 400 and not Injury.objects.exists()


def test_injury_create_and_edit(cl):
    r = post(cl, "/calendar/marker/injury/", {"body_part": "left knee", "severity": "moderate",
                                               "date_started": d(10).isoformat(), "affects_cycling": True}).json()
    inj = Injury.objects.get(id=r["id"])
    assert inj.severity == "moderate" and inj.affects_running and inj.affects_cycling
    post(cl, "/calendar/marker/injury/", {"id": inj.id, "body_part": "left knee", "date_started": d(10).isoformat(),
                                          "date_resolved": d(2).isoformat()})
    inj.refresh_from_db()
    assert inj.date_resolved == d(2) and inj.severity is None


# --- the agent's side -----------------------------------------------------------------

@pytest.mark.parametrize("name,required", [("log_illness", []), ("resolve_illness", []), ("log_alcohol", ["drinks"])])
def test_new_tools_registered_in_all_three_places(name, required):
    assert name in TOOL_FUNCTIONS
    schema = next(t for t in TOOL_DEFINITIONS if t["name"] == name)
    assert schema["input_schema"]["required"] == required


@pytest.mark.django_db
def test_illness_tools_open_update_and_close_one_period():
    assert "starting" in execute_tool("log_illness", {"symptoms": "sore throat", "started_days_ago": 1})
    execute_tool("log_illness", {"systemic": True})
    ill = Illness.objects.get()
    assert ill.date_started == d(1) and ill.systemic and ill.symptoms == "sore throat"
    execute_tool("resolve_illness", {})
    ill.refresh_from_db()
    assert ill.date_resolved == TODAY
    assert execute_tool("log_illness", {"started_days_ago": 30}).startswith("Invalid")


@pytest.mark.django_db
def test_log_alcohol_sets_the_days_total():
    execute_tool("log_alcohol", {"drinks": 3, "days_ago": 1})
    execute_tool("log_alcohol", {"drinks": 2, "days_ago": 1})
    assert DailyFeeling.objects.get(date=d(1)).alcohol_drinks == 2
    assert execute_tool("log_alcohol", {"drinks": 2, "days_ago": 9}).startswith("Invalid")


@pytest.mark.django_db
def test_context_has_illness_and_drinks():
    from coach.context import build_context
    Illness.objects.create(date_started=d(1), symptoms="cold")
    Illness.objects.create(date_started=d(60), date_resolved=d(50))                 # long over
    DailyFeeling.objects.create(date=d(1), alcohol_drinks=4)
    ctx = build_context()
    assert [i["symptoms"] for i in ctx["illness"]] == ["cold"]
    assert ctx["daily_feelings_last_14_days"][0]["alcohol_drinks"] == 4


@pytest.mark.django_db
def test_insight_notes_mention_illness_and_drinks():
    from coach import insights
    Illness.objects.create(date_started=d(2), symptoms="cold")
    DailyFeeling.objects.create(date=d(1), alcohol_drinks=5)
    text = json.dumps(insights.coach_notes(insights._last_days(TODAY)))
    assert "cold" in text and '"alcohol_drinks": 5' in text
