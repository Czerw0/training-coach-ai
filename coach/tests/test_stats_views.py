import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from coach.models import Goal, Injury, PlannedSession
from sync.models import Activity


@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


def test_stats_page_requires_login(client):
    resp = client.get(reverse("stats_page"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


def test_stats_data_requires_login(client):
    resp = client.get(reverse("stats_data"))
    assert resp.status_code == 302


@pytest.mark.django_db
def test_stats_page_renders_with_persistent_nav(client, user):
    client.force_login(user)
    resp = client.get(reverse("stats_page"))
    assert resp.status_code == 200
    content = resp.content.decode()
    for marker in ['class="nav-link', 'href="/calendar/"', 'href="/usage/"']:
        assert marker in content


@pytest.mark.django_db
def test_stats_data_returns_expected_top_level_keys(client, user):
    client.force_login(user)
    resp = client.get(reverse("stats_data"))
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"summary", "by_type_90d", "weekly_volume", "adherence"}
    assert set(data["summary"].keys()) == {
        "total_activities", "first_activity_date", "active_goals", "active_injuries",
    }


@pytest.mark.django_db
def test_stats_data_summary_counts_are_correct(client, user):
    client.force_login(user)
    Goal.objects.create(title="60 VO2max", is_active=True)
    Goal.objects.create(title="old goal", is_active=False)
    Injury.objects.create(date_started=datetime.date.today(), body_part="knee", severity="minor")

    resp = client.get(reverse("stats_data"))
    summary = resp.json()["summary"]
    assert summary["active_goals"] == 1
    assert summary["active_injuries"] == 1


@pytest.mark.django_db
def test_stats_data_by_type_90d_groups_and_counts(client, user):
    client.force_login(user)
    now = datetime.datetime.now()
    Activity.objects.create(garmin_id="1", start_time=now, activity_type="strength_training", duration_seconds=3600)
    Activity.objects.create(garmin_id="2", start_time=now, activity_type="strength_training", duration_seconds=1800)
    Activity.objects.create(garmin_id="3", start_time=now, activity_type="inline_skating", duration_seconds=2400)
    # outside the 90-day window — must be excluded
    Activity.objects.create(
        garmin_id="4", start_time=now - datetime.timedelta(days=200),
        activity_type="road_biking", duration_seconds=3600,
    )

    resp = client.get(reverse("stats_data"))
    by_type = {row["activity_type"]: row for row in resp.json()["by_type_90d"]}
    assert by_type["strength_training"]["n"] == 2
    assert by_type["strength_training"]["minutes"] == 90  # (3600+1800)/60
    assert by_type["inline_skating"]["n"] == 1
    assert "road_biking" not in by_type


@pytest.mark.django_db
def test_stats_data_adherence_counts_matched_session(client, user):
    client.force_login(user)
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    PlannedSession.objects.create(date=yesterday, activity_type="cycling", title="Ride")
    Activity.objects.create(
        start_time=datetime.datetime.combine(yesterday, datetime.time(10, 0)),
        activity_type="road_biking", duration_seconds=3600,
    )

    resp = client.get(reverse("stats_data"))
    adherence = resp.json()["adherence"]
    assert adherence["matched"] == 1
    assert adherence["total"] == 1
    assert adherence["rate"] == 100
    assert adherence["missed"] == []


@pytest.mark.django_db
def test_stats_data_adherence_lists_unmatched_session_as_missed(client, user):
    client.force_login(user)
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    PlannedSession.objects.create(date=yesterday, activity_type="gym_legs", title="Leg day")

    resp = client.get(reverse("stats_data"))
    adherence = resp.json()["adherence"]
    assert adherence["matched"] == 0
    assert adherence["total"] == 1
    assert adherence["rate"] == 0
    assert adherence["missed"] == [{"date": yesterday.isoformat(), "title": "Leg day", "activity_type": "gym_legs"}]


@pytest.mark.django_db
def test_stats_data_adherence_excludes_rest_days_and_future_sessions(client, user):
    client.force_login(user)
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    PlannedSession.objects.create(date=yesterday, activity_type="rest", title="Rest")
    PlannedSession.objects.create(date=tomorrow, activity_type="cycling", title="Future ride")

    resp = client.get(reverse("stats_data"))
    adherence = resp.json()["adherence"]
    assert adherence["total"] == 0
    assert adherence["rate"] is None
