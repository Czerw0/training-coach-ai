import datetime
import json

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from coach.models import PlannedExercise, PlannedSession
from coach.tools import PLANNING_WINDOW_DAYS
from sync.models import Activity, Exercise


@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


def test_calendar_events_requires_login(client):
    resp = client.get(reverse("calendar_events"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_calendar_page_renders_with_new_ui_markup(client, user):
    client.force_login(user)
    resp = client.get(reverse("calendar_page"))
    assert resp.status_code == 200
    content = resp.content.decode()
    for marker in ["exercise-rows", "exercise-options", "add-exercise-btn"]:
        assert marker in content, f"expected '{marker}' in rendered calendar page"
    for marker in ['class="nav-link', 'href="/stats/"', 'href="/usage/"']:
        assert marker in content
    assert "week-summary" not in content
    assert 'class="back"' not in content


@pytest.mark.django_db
def test_calendar_events_marks_activities_non_editable_and_planned_editable(client, user):
    client.force_login(user)
    Activity.objects.create(
        start_time=datetime.datetime.now(), activity_type="cycling", duration_seconds=3600,
    )
    PlannedSession.objects.create(date=datetime.date.today(), activity_type="cycling", title="Ride")

    resp = client.get(reverse("calendar_events"))
    events = resp.json()

    activity_events = [e for e in events if e["extendedProps"]["kind"] == "activity"]
    planned_events = [e for e in events if e["extendedProps"]["kind"] == "planned"]
    assert activity_events[0]["editable"] is False
    assert "editable" not in planned_events[0] or planned_events[0].get("editable") is not False


@pytest.mark.django_db
def test_calendar_events_planned_title_names_who_planned_it_correctly(client, user):
    # Regression test: the title used to compare created_by against "user",
    # but real values are "human" (UI path) / "ai" (LLM tool path) / a
    # legacy "coach" value — so it silently always said "Coach", even for
    # sessions a human planned via the UI.
    client.force_login(user)
    PlannedSession.objects.create(
        date=datetime.date.today(), activity_type="cycling", title="Ride", created_by="human",
    )
    PlannedSession.objects.create(
        date=datetime.date.today() + datetime.timedelta(days=1),
        activity_type="cycling", title="Intervals", created_by="ai",
    )

    resp = client.get(reverse("calendar_events"))
    planned = {e["extendedProps"]["title"]: e["title"] for e in resp.json() if e["extendedProps"]["kind"] == "planned"}

    assert planned["Ride"] == "You · Ride"
    assert planned["Intervals"] == "Coach · Intervals"
    # no colour-bubble emoji in the title
    assert "🟢" not in planned["Ride"] and "🟡" not in planned["Ride"]


@pytest.mark.django_db
def test_calendar_events_includes_exercises_in_extended_props(client, user):
    client.force_login(user)
    session = PlannedSession.objects.create(
        date=datetime.date.today(), activity_type="gym_legs", title="Legs",
    )
    PlannedExercise.objects.create(session=session, name="Barbell Back Squat", sets=4, reps=6, order=0)

    resp = client.get(reverse("calendar_events"))
    planned = [e for e in resp.json() if e["extendedProps"]["kind"] == "planned"][0]
    assert planned["extendedProps"]["exercises"] == [
        {"name": "Barbell Back Squat", "sets": 4, "reps": 6, "weight_kg": None, "notes": ""}
    ]


@pytest.mark.django_db
def test_save_planned_session_writes_planned_exercise_rows_for_gym_type(client, user):
    client.force_login(user)
    payload = {
        "date": datetime.date.today().isoformat(),
        "activity_type": "gym_upper",
        "title": "Push day",
        "exercises": [
            {"name": "Bench Press", "sets": 4, "reps": 6, "weight_kg": 60},
            {"name": "Overhead Press", "sets": 3, "reps": 8},
        ],
    }
    resp = client.post(reverse("save_planned_session"), data=json.dumps(payload), content_type="application/json")
    assert resp.status_code == 200
    session = PlannedSession.objects.get()
    assert session.exercises.count() == 2
    assert list(session.exercises.values_list("name", flat=True)) == ["Bench Press", "Overhead Press"]


@pytest.mark.django_db
def test_save_planned_session_replaces_exercises_on_edit(client, user):
    client.force_login(user)
    base_payload = {
        "date": datetime.date.today().isoformat(), "activity_type": "gym_legs", "title": "Legs",
        "exercises": [{"name": "Barbell Back Squat", "sets": 4, "reps": 6}],
    }
    client.post(reverse("save_planned_session"), data=json.dumps(base_payload), content_type="application/json")
    session = PlannedSession.objects.get()

    edit_payload = {**base_payload, "id": session.id, "exercises": [{"name": "Leg Press", "sets": 3, "reps": 10}]}
    client.post(reverse("save_planned_session"), data=json.dumps(edit_payload), content_type="application/json")

    session.refresh_from_db()
    assert session.exercises.count() == 1
    assert session.exercises.get().name == "Leg Press"


@pytest.mark.django_db
def test_move_planned_session_updates_date_within_window(client, user):
    client.force_login(user)
    session = PlannedSession.objects.create(date=datetime.date.today(), activity_type="cycling")
    new_date = datetime.date.today() + datetime.timedelta(days=3)

    resp = client.post(
        reverse("move_planned_session"),
        data=json.dumps({"id": session.id, "date": new_date.isoformat()}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.date == new_date


@pytest.mark.django_db
def test_move_planned_session_allows_dates_beyond_the_llm_planning_window(client, user):
    # PLANNING_WINDOW_DAYS (14 days) is the LLM's visible date horizon — it
    # must NOT restrict a human dragging on the real calendar grid, which can
    # see and legitimately target dates far beyond that (calendar_events()
    # itself shows sessions with no date filter at all).
    client.force_login(user)
    session = PlannedSession.objects.create(date=datetime.date.today(), activity_type="cycling")
    far_future = datetime.date.today() + datetime.timedelta(days=PLANNING_WINDOW_DAYS + 30)

    resp = client.post(
        reverse("move_planned_session"),
        data=json.dumps({"id": session.id, "date": far_future.isoformat()}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    session.refresh_from_db()
    assert session.date == far_future


@pytest.mark.django_db
def test_move_planned_session_rejects_a_date_in_the_past(client, user):
    client.force_login(user)
    session = PlannedSession.objects.create(date=datetime.date.today(), activity_type="cycling")
    yesterday = datetime.date.today() - datetime.timedelta(days=1)

    resp = client.post(
        reverse("move_planned_session"),
        data=json.dumps({"id": session.id, "date": yesterday.isoformat()}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    session.refresh_from_db()
    assert session.date == datetime.date.today()


@pytest.mark.django_db
def test_exercise_options_endpoint_returns_catalog(client, user):
    client.force_login(user)
    Exercise.objects.create(name="Barbell Back Squat", category="legs")
    resp = client.get(reverse("exercise_options"))
    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()]
    assert "Barbell Back Squat" in names
