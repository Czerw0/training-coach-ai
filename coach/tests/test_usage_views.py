import pytest
from django.contrib.auth.models import User
from django.urls import reverse

from coach.models import ApiUsage


@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


@pytest.fixture
def usage_row(db):
    return ApiUsage.objects.create(
        model="claude-sonnet-5",
        input_tokens=1000,
        cache_creation_tokens=200,
        cache_read_tokens=50,
        output_tokens=300,
        cost_usd=0.0123,
        api_calls=2,
        user_message="how's my week looking?",
        tools_used="log_daily_feeling",
        prompt_version="v1.2.2@deadbeef",
        config_version="v2-notemp-cache",
        tool_trace=[{"tool": "log_daily_feeling", "input": {"energy_level": 7}, "result": "ok"}],
        final_text="Logged it, good energy today.",
    )


def test_usage_detail_page_requires_login(client, usage_row):
    resp = client.get(reverse("usage_detail_page", args=[usage_row.id]))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


def test_usage_detail_page_renders_for_logged_in_user(client, user, usage_row):
    client.force_login(user)
    resp = client.get(reverse("usage_detail_page", args=[usage_row.id]))
    assert resp.status_code == 200
    assert str(usage_row.id).encode() in resp.content


def test_usage_detail_page_404_for_missing_row(client, user):
    client.force_login(user)
    resp = client.get(reverse("usage_detail_page", args=[999999]))
    assert resp.status_code == 404


def test_usage_detail_data_requires_login(client, usage_row):
    resp = client.get(reverse("usage_detail_data", args=[usage_row.id]))
    assert resp.status_code == 302


def test_usage_detail_data_returns_full_trace(client, user, usage_row):
    client.force_login(user)
    resp = client.get(reverse("usage_detail_data", args=[usage_row.id]))
    assert resp.status_code == 200
    data = resp.json()

    assert data["id"] == usage_row.id
    assert data["model"] == "claude-sonnet-5"
    assert data["config_version"] == "v2-notemp-cache"
    assert data["prompt_version"] == "v1.2.2@deadbeef"
    assert data["cost"] == pytest.approx(0.0123)
    assert data["cache_read"] == 50
    assert data["user_message"] == "how's my week looking?"
    assert data["final_text"] == "Logged it, good energy today."
    assert data["tool_trace"] == [
        {"tool": "log_daily_feeling", "input": {"energy_level": 7}, "result": "ok"}
    ]


def test_usage_detail_data_404_for_missing_row(client, user):
    client.force_login(user)
    resp = client.get(reverse("usage_detail_data", args=[999999]))
    assert resp.status_code == 404


@pytest.mark.django_db
def test_usage_page_renders_with_persistent_nav(client, user):
    client.force_login(user)
    resp = client.get(reverse("usage_page"))
    assert resp.status_code == 200
    content = resp.content.decode()
    for marker in ['class="nav-link', 'href="/stats/"', 'href="/calendar/"']:
        assert marker in content
    # the old single "back to Coach" pill is gone, replaced by the shared nav
    assert 'class="back"' not in content
