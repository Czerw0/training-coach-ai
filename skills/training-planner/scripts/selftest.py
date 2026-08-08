#!/usr/bin/env python3
"""Self-test for the deterministic checker. Plain-python, no pytest needed:

    python selftest.py

Runs against the real reference/sessions files, so it also catches a leaf whose
frontmatter stops parsing. Exit 0 = all pass.
"""
from datetime import datetime

import check_week


def _week(*pairs):
    return [{"id": sid, "start": datetime.fromisoformat(t)} for sid, t in pairs]


def _kinds(violations, severity=None):
    return {v["kind"] for v in violations if severity is None or v["severity"] == severity}


CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def clean_week_has_no_errors():
    v = check_week.check(_week(
        ("gym/lower-max-strength", "2026-08-10T17:00"),
        ("cycling/endurance", "2026-08-11T09:00"),
        ("running/intervals", "2026-08-15T10:00"),
    ))
    assert _kinds(v, "error") == set(), v


@case
def spacing_violation_is_an_error():
    # eccentric -> intervals needs 72 h; give it 37 h
    v = check_week.check(_week(
        ("gym/lower-eccentric", "2026-08-10T18:00"),
        ("running/intervals", "2026-08-12T07:00"),
    ))
    assert "spacing" in _kinds(v, "error"), v


@case
def same_day_conflict_close_is_error_far_is_warning():
    close = check_week.check(_week(
        ("running/intervals", "2026-08-12T07:00"),
        ("plyometrics/intensive", "2026-08-12T10:00"),  # 3 h apart
    ))
    assert "same-day-conflict" in _kinds(close, "error"), close
    far = check_week.check(_week(
        ("running/intervals", "2026-08-12T07:00"),
        ("plyometrics/intensive", "2026-08-12T20:00"),  # 13 h apart, same day
    ))
    # >=6 h apart downgrades to warning (spacing may still error separately)
    assert "same-day-conflict" in _kinds(far, "warning"), far


@case
def two_high_mechanical_saturates_as_error():
    v = check_week.check(_week(
        ("running/intervals", "2026-08-12T07:00"),
        ("plyometrics/intensive", "2026-08-13T07:00"),  # 24 h; both mech high
    ))
    sat = [x for x in v if x["kind"] == "axis-saturation" and x["axis"] == "mechanical"]
    assert sat and sat[0]["severity"] == "error", v


@case
def easy_filler_does_not_saturate():
    # one lift + easy spins must not trip a saturation warning
    v = check_week.check(_week(
        ("gym/lower-max-strength", "2026-08-10T17:00"),
        ("cycling/endurance", "2026-08-11T09:00"),
        ("cycling/endurance", "2026-08-11T18:00"),
    ))
    assert not any(x["kind"] == "axis-saturation" for x in v), v


@case
def unknown_session_warns_not_crashes():
    v = check_week.check(_week(
        ("gym/does-not-exist", "2026-08-10T17:00"),
        ("cycling/endurance", "2026-08-11T09:00"),
    ))
    assert "unknown-session" in _kinds(v, "warning"), v


@case
def stricter_spacing_wins_on_disagreement():
    # lower-max declares intervals:24, intervals declares nothing back for it;
    # a 20 h gap must still flag against the 24 h floor
    v = check_week.check(_week(
        ("gym/lower-max-strength", "2026-08-10T17:00"),
        ("running/intervals", "2026-08-11T13:00"),  # 20 h
    ))
    assert "spacing" in _kinds(v, "error"), v


def main():
    failed = 0
    for fn in CASES:
        try:
            fn()
            print(f"ok   {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
