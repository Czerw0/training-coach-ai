import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.fixture
def user(db):
    return User.objects.create_user(username="athlete", password="pw12345")


def test_chat_page_requires_login(client):
    resp = client.get(reverse("chat_page"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp.url


@pytest.mark.django_db
def test_chat_page_renders_with_persistent_nav_and_no_dead_code(client, user):
    client.force_login(user)
    resp = client.get(reverse("chat_page"))
    assert resp.status_code == 200
    content = resp.content.decode()

    for marker in ['class="nav-link', 'href="/stats/"', 'href="/usage/"', 'href="/calendar/"']:
        assert marker in content, f"expected '{marker}' in rendered chat page"

    # dead code from the old single-page tab-switcher design must be gone
    for dead_marker in ['view-toggle', 'id="view-calendar"', 'id="cal-btn"', 'id="use-btn"']:
        assert dead_marker not in content, f"'{dead_marker}' should have been removed"


@pytest.mark.django_db
def test_chat_page_renders_trace_panel_markup(client, user):
    client.force_login(user)
    resp = client.get(reverse("chat_page"))
    content = resp.content.decode()
    for marker in ['id="trace-panel"', 'id="trace-body"', 'id="trace-toggle"']:
        assert marker in content


def _fake_usage(usage_kwargs=None):
    return SimpleNamespace(
        input_tokens=100, cache_creation_input_tokens=0,
        cache_read_input_tokens=0, output_tokens=50,
    )


@pytest.mark.django_db
def test_chat_message_response_includes_trace(client, user):
    client.force_login(user)
    response = SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="thinking", thinking="Athlete seems fine, no action needed."),
            SimpleNamespace(type="text", text="Sounds good!"),
        ],
        usage=_fake_usage(),
    )
    with patch("coach.agent.client.messages.create", return_value=response):
        resp = client.post(
            reverse("chat_message"),
            data=json.dumps({"message": "just checking in"}),
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"] == "Sounds good!"
    assert data["trace"]["round_notes"] == [
        {"round": 1, "text": "Athlete seems fine, no action needed."}
    ]
    assert data["trace"]["tool_trace"] == []
