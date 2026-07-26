from types import SimpleNamespace
from unittest.mock import patch

import pytest

from coach.agent import CONFIG_VERSION, PROMPT_TAG, chat, compute_cost
from coach.models import ApiUsage, CoachRecommendation


def make_usage(input_tokens=100, cache_creation_input_tokens=0,
               cache_read_input_tokens=0, output_tokens=50):
    return SimpleNamespace(
        input_tokens=input_tokens,
        cache_creation_input_tokens=cache_creation_input_tokens,
        cache_read_input_tokens=cache_read_input_tokens,
        output_tokens=output_tokens,
    )


def make_text_response(text, **usage_kwargs):
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=text)],
        usage=make_usage(**usage_kwargs),
    )


def make_tool_use_response(tool_name, tool_input, tool_id="tool_1", **usage_kwargs):
    return SimpleNamespace(
        stop_reason="tool_use",
        content=[SimpleNamespace(type="tool_use", name=tool_name, input=tool_input, id=tool_id)],
        usage=make_usage(**usage_kwargs),
    )


# --- pricing (backlog item 2: Sonnet cost constants) ---

def test_compute_cost_input_only():
    assert compute_cost(1_000_000, 0, 0, 0) == pytest.approx(2.00)


def test_compute_cost_output_only():
    assert compute_cost(0, 0, 0, 1_000_000) == pytest.approx(10.00)


def test_compute_cost_cache_write_and_read():
    assert compute_cost(0, 1_000_000, 1_000_000, 0) == pytest.approx(2.70)


def test_compute_cost_mixed_turn():
    # 100k in + 10k out: 0.20 + 0.10 = 0.30 at Sonnet 5 intro pricing
    assert compute_cost(100_000, 0, 0, 10_000) == pytest.approx(0.30)


# --- config_version / tool_trace recording (backlog items 1 & 3) ---

@pytest.mark.django_db
def test_chat_records_config_version_and_final_text():
    response = make_text_response("Sounds good.")
    with patch("coach.agent.client.messages.create", return_value=response):
        final_text, tools_used = chat("How's my week looking?")

    assert final_text == "Sounds good."
    assert tools_used == []
    row = ApiUsage.objects.latest("created_at")
    assert row.config_version == CONFIG_VERSION
    assert row.prompt_version == PROMPT_TAG
    assert row.final_text == "Sounds good."
    assert row.tool_trace == []


@pytest.mark.django_db
def test_chat_captures_tool_trace_and_final_reply():
    tool_response = make_tool_use_response("log_daily_feeling", {"energy_level": 7})
    final_response = make_text_response("Logged it.")
    with patch("coach.agent.client.messages.create",
               side_effect=[tool_response, final_response]), \
         patch("coach.agent.execute_tool", return_value="ok") as mock_exec:
        final_text, tools_used = chat("feeling good today, energy 7")

    assert tools_used == ["log_daily_feeling"]
    mock_exec.assert_called_once_with("log_daily_feeling", {"energy_level": 7})
    row = ApiUsage.objects.latest("created_at")
    assert row.tool_trace == [
        {"tool": "log_daily_feeling", "input": {"energy_level": 7}, "result": "ok"}
    ]
    assert CoachRecommendation.objects.filter(recommendation="Logged it.").exists()


# --- "(test)" prefix: code-level bypass, not a prompt request ---

@pytest.mark.django_db
def test_test_prefix_skips_coach_recommendation_write():
    response = make_text_response("This is a test reply.")
    before = CoachRecommendation.objects.count()
    with patch("coach.agent.client.messages.create", return_value=response):
        chat("(test) does this work?")
    assert CoachRecommendation.objects.count() == before


@pytest.mark.django_db
def test_test_prefix_never_calls_real_tool():
    tool_response = make_tool_use_response("create_planned_session", {"date": "2026-08-01"})
    final_response = make_text_response("Simulated.")
    with patch("coach.agent.client.messages.create",
               side_effect=[tool_response, final_response]), \
         patch("coach.agent.execute_tool") as mock_exec:
        final_text, tools_used = chat("(test) plan a session")

    mock_exec.assert_not_called()
    assert tools_used == ["create_planned_session"]
    row = ApiUsage.objects.latest("created_at")
    assert "not executed" in row.tool_trace[0]["result"]


@pytest.mark.django_db
def test_test_prefix_is_case_insensitive_with_leading_whitespace():
    response = make_text_response("ok")
    before = CoachRecommendation.objects.count()
    with patch("coach.agent.client.messages.create", return_value=response):
        chat("  (TEST) ping")
    assert CoachRecommendation.objects.count() == before


@pytest.mark.django_db
def test_non_test_message_still_writes_recommendation():
    response = make_text_response("Real advice.")
    before = CoachRecommendation.objects.count()
    with patch("coach.agent.client.messages.create", return_value=response):
        chat("what should I do today?")
    assert CoachRecommendation.objects.count() == before + 1
