import datetime

import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

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


@pytest.mark.django_db
def test_usage_page_renders_filter_bar_and_reset_button(client, user):
    client.force_login(user)
    resp = client.get(reverse("usage_page"))
    content = resp.content.decode()
    for marker in ['id="f-model"', 'id="f-config"', 'id="f-since"', 'id="f-until"', 'id="f-reset"']:
        assert marker in content


def _make_usage_row(model, config_version, created_at, cost=0.01):
    row = ApiUsage.objects.create(
        model=model, config_version=config_version, cost_usd=cost,
        input_tokens=10, output_tokens=10,
    )
    ApiUsage.objects.filter(pk=row.pk).update(created_at=created_at)  # bypass auto_now_add
    return row


@pytest.mark.django_db
def test_usage_data_filters_by_model(client, user):
    client.force_login(user)
    now = timezone.now()
    _make_usage_row("claude-sonnet-5", "v3-thinking-1024", now)
    _make_usage_row("claude-haiku-4-5", "v3-thinking-1024", now)

    resp = client.get(reverse("usage_data"), {"model": "claude-haiku-4-5"})
    data = resp.json()
    assert data["summary"]["total_turns"] == 1
    assert len(data["by_config"]) == 1
    assert data["by_config"][0]["model"] == "claude-haiku-4-5"


@pytest.mark.django_db
def test_usage_data_filters_by_config_version(client, user):
    client.force_login(user)
    now = timezone.now()
    _make_usage_row("claude-sonnet-5", "v2-notemp-cache", now)
    _make_usage_row("claude-sonnet-5", "v3-thinking-1024", now)

    resp = client.get(reverse("usage_data"), {"config_version": "v3-thinking-1024"})
    assert resp.json()["summary"]["total_turns"] == 1


@pytest.mark.django_db
def test_usage_data_filters_by_date_range(client, user):
    client.force_login(user)
    today = timezone.now()
    old = today - datetime.timedelta(days=10)
    _make_usage_row("claude-sonnet-5", "v3-thinking-1024", today)
    _make_usage_row("claude-sonnet-5", "v3-thinking-1024", old)

    since = (today - datetime.timedelta(days=1)).date().isoformat()
    resp = client.get(reverse("usage_data"), {"since": since})
    assert resp.json()["summary"]["total_turns"] == 1


@pytest.mark.django_db
def test_usage_data_filter_options_reflect_full_table_even_when_filtered(client, user):
    client.force_login(user)
    now = timezone.now()
    _make_usage_row("claude-sonnet-5", "v2-notemp-cache", now)
    _make_usage_row("claude-haiku-4-5", "v3-thinking-1024", now)

    resp = client.get(reverse("usage_data"), {"model": "claude-sonnet-5"})
    data = resp.json()
    assert data["summary"]["total_turns"] == 1  # filtered view
    assert set(data["filter_options"]["models"]) == {"claude-sonnet-5", "claude-haiku-4-5"}
    assert set(data["filter_options"]["config_versions"]) == {"v2-notemp-cache", "v3-thinking-1024"}


@pytest.mark.django_db
def test_usage_data_no_filters_returns_everything(client, user):
    client.force_login(user)
    now = timezone.now()
    _make_usage_row("claude-sonnet-5", "v2-notemp-cache", now)
    _make_usage_row("claude-haiku-4-5", "v3-thinking-1024", now)

    resp = client.get(reverse("usage_data"))
    assert resp.json()["summary"]["total_turns"] == 2
