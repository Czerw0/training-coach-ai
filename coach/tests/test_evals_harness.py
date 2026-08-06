import datetime

import pytest

from coach.evals.harness import (
    check_dates_match_weekdays,
    check_expect_tools,
    check_forbid_text_patterns,
    check_forbid_tools,
    check_no_fabricated_completion,
    check_numbers_grounded_in_tools,
    check_require_text_patterns,
    check_tool_order,
    load_cases,
    resolve_date_placeholder,
    run_case,
)
from coach.models import ApiUsage, PlannedSession


def test_load_cases_returns_nonempty_list_with_unique_ids():
    cases = load_cases()
    assert len(cases) >= 10
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids))


def test_expect_tools_ok_when_all_present():
    ok, detail = check_expect_tools(["log_daily_feeling", "append_athlete_note"], ["log_daily_feeling"])
    assert ok
    assert detail == "ok"


def test_expect_tools_fails_when_missing():
    ok, detail = check_expect_tools(["append_athlete_note"], ["log_daily_feeling"])
    assert not ok
    assert "log_daily_feeling" in detail


def test_forbid_tools_fails_when_hit():
    ok, detail = check_forbid_tools(["create_planned_session"], ["clear_planned_sessions"])
    assert ok  # forbidden tool wasn't called
    ok2, _ = check_forbid_tools(["clear_planned_sessions"], ["clear_planned_sessions"])
    assert not ok2


def test_tool_order_passes_for_correct_sequence():
    trace = [{"tool": "clear_planned_sessions"}, {"tool": "create_planned_session"}]
    ok, detail = check_tool_order(trace, ["clear_planned_sessions", "create_planned_session"])
    assert ok, detail


def test_tool_order_fails_for_reversed_sequence():
    trace = [{"tool": "create_planned_session"}, {"tool": "clear_planned_sessions"}]
    ok, detail = check_tool_order(trace, ["clear_planned_sessions", "create_planned_session"])
    assert not ok


def test_tool_order_fails_when_a_tool_never_ran():
    trace = [{"tool": "create_planned_session"}]
    ok, detail = check_tool_order(trace, ["clear_planned_sessions", "create_planned_session"])
    assert not ok
    assert "never called" in detail


def test_dates_match_weekdays_passes_for_correct_pair():
    # 2026-08-05 is a Wednesday
    trace = [{"tool": "create_planned_session", "input": {"date": "2026-08-05", "weekday": "Wednesday"}}]
    ok, detail = check_dates_match_weekdays(trace)
    assert ok, detail


def test_dates_match_weekdays_fails_for_wrong_weekday():
    trace = [{"tool": "create_planned_session", "input": {"date": "2026-08-05", "weekday": "Monday"}}]
    ok, detail = check_dates_match_weekdays(trace)
    assert not ok
    assert "2026-08-05" in detail


def test_dates_match_weekdays_ignores_non_calendar_tools():
    trace = [{"tool": "log_daily_feeling", "input": {"energy_level": 7}}]
    ok, detail = check_dates_match_weekdays(trace)
    assert ok


def test_forbid_text_patterns_catches_a_hit():
    ok, detail = check_forbid_text_patterns("Maybe go for a run today!", [r"\bgo (for|out) (for )?a run\b"])
    assert not ok


def test_forbid_text_patterns_ok_when_no_hit():
    ok, detail = check_forbid_text_patterns("Let's do an easy spin instead.", [r"\bgo (for|out) (for )?a run\b"])
    assert ok


def test_require_text_patterns_fails_when_missing():
    ok, detail = check_require_text_patterns("Sounds good.", [r"\brest\b"])
    assert not ok


def test_no_fabricated_completion_fails_when_claim_without_tool():
    ok, detail = check_no_fabricated_completion("Done, saved that for you!", [])
    assert not ok
    assert "no tool was called" in detail


def test_no_fabricated_completion_passes_when_tool_ran():
    ok, detail = check_no_fabricated_completion("Done, saved that for you!", ["create_planned_session"])
    assert ok


def test_no_fabricated_completion_passes_with_no_claim():
    ok, detail = check_no_fabricated_completion("Here's what I'd suggest instead.", [])
    assert ok


def test_numbers_grounded_passes_when_wattage_in_tool_result():
    trace = [{"tool": "get_workout_detail", "result": "4x8min @ 250w with 3min recovery"}]
    ok, detail = check_numbers_grounded_in_tools("Do 4 reps of 8 minutes at 250w.", trace)
    assert ok, detail


def test_numbers_grounded_fails_for_invented_wattage():
    trace = [{"tool": "get_workout_detail", "result": "4x8min @ 250w with 3min recovery"}]
    ok, detail = check_numbers_grounded_in_tools("Push hard at 400w for this one.", trace)
    assert not ok
    assert "400" in detail


def test_numbers_grounded_ok_when_no_wattage_mentioned():
    ok, detail = check_numbers_grounded_in_tools("Just an easy recovery spin today.", [])
    assert ok


@pytest.mark.parametrize("key,expected_weekday", [
    ("@today", None),
    ("@tomorrow", None),
])
def test_resolve_date_placeholder_relative(key, expected_weekday):
    today = datetime.date(2026, 8, 3)  # a Monday
    resolved = resolve_date_placeholder(key, today)
    assert resolved is not None
    datetime.date.fromisoformat(resolved)  # must be a valid ISO date


def test_resolve_date_placeholder_next_weekday_skips_today():
    today = datetime.date(2026, 8, 5)  # a Wednesday
    resolved = resolve_date_placeholder("@next_wednesday", today)
    # "next" Wednesday from a Wednesday should be 7 days out, not today
    assert resolved == "2026-08-12"


def test_resolve_date_placeholder_next_weekday_this_week():
    today = datetime.date(2026, 8, 3)  # a Monday
    resolved = resolve_date_placeholder("@next_wednesday", today)
    assert resolved == "2026-08-05"


def test_resolve_date_placeholder_passthrough_for_literal_dates():
    assert resolve_date_placeholder("2026-09-01", datetime.date(2026, 8, 3)) == "2026-09-01"


def test_resolve_date_placeholder_unknown_raises():
    with pytest.raises(ValueError):
        resolve_date_placeholder("@not_a_real_placeholder", datetime.date(2026, 8, 3))


# --- cross-case isolation: run_case() must roll back everything it did ---

def _fake_chat_that_writes_a_planned_session(message, history):
    """Stand-in for coach.agent.chat — no real API call. Simulates the model
    calling a DB-writing tool (like create_planned_session) mid-turn."""
    ApiUsage.objects.create(model="fake", tool_trace=[])
    PlannedSession.objects.create(
        date=datetime.date.today(), activity_type="cycling", title="from case A"
    )
    return "WROTE", ["create_planned_session"]


def _fake_chat_that_checks_for_leaked_state(message, history):
    """Stand-in for coach.agent.chat — no real API call. Writes the ApiUsage
    row run_case() expects to read, and reports whether a PlannedSession
    already exists (i.e. leaked in from an earlier case)."""
    ApiUsage.objects.create(model="fake", tool_trace=[])
    final_text = "LEAK" if PlannedSession.objects.exists() else "CLEAN"
    return final_text, []


@pytest.mark.django_db
def test_run_case_does_not_leak_state_between_cases():
    case_a = {"id": "writes_a_planned_session", "turns": ["irrelevant"]}
    case_b = {"id": "should_see_a_clean_db", "turns": ["irrelevant"]}

    result_a = run_case(case_a, _fake_chat_that_writes_a_planned_session)
    result_b = run_case(case_b, _fake_chat_that_checks_for_leaked_state)

    assert result_a["final_text"] == "WROTE"
    assert result_b["final_text"] == "CLEAN"  # must NOT see case A's PlannedSession
    assert PlannedSession.objects.count() == 0  # nothing survives past either case
