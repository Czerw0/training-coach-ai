"""Eval harness: send golden-case messages through the real chat() loop
(real API calls, real cost — this is deliberately not mocked) and check
tool calls / reply text against declarative assertions.

Golden cases live in cases.json. Run via `python manage.py run_evals`,
which wraps this in an isolated Django test database so nothing here ever
touches real athlete data.
"""
import datetime
import json
import re
from pathlib import Path

CASES_PATH = Path(__file__).parent / "cases.json"

COMPLETION_CLAIM_RE = re.compile(
    r"\b(done|saved|scheduled|added|logged|updated|booked|set that up)\b", re.IGNORECASE
)
NUMBER_WATT_RE = re.compile(r"(\d+)\s*w(?:atts?)?\b", re.IGNORECASE)

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def load_cases():
    return json.loads(CASES_PATH.read_text())


# ---- pure check functions: (ok: bool, detail: str) ----

def check_expect_tools(tools_used, expect):
    missing = [t for t in expect if t not in tools_used]
    return (not missing, "ok" if not missing else f"missing expected tool call(s): {missing}")


def check_forbid_tools(tools_used, forbid):
    hit = [t for t in forbid if t in tools_used]
    return (not hit, "ok" if not hit else f"called forbidden tool(s): {hit}")


def check_tool_order(tool_trace, order):
    names = [t["tool"] for t in tool_trace]
    positions = []
    for name in order:
        if name not in names:
            return (False, f"'{name}' was never called — can't check ordering")
        positions.append(names.index(name))
    if positions != sorted(positions):
        return (False, f"expected order {order}, actual tool sequence was {names}")
    return (True, "ok")


def check_dates_match_weekdays(tool_trace):
    bad = []
    for call in tool_trace:
        if call["tool"] not in ("create_planned_session", "clear_planned_sessions"):
            continue
        date_str = call["input"].get("date")
        weekday = call["input"].get("weekday")
        if not date_str or not weekday:
            bad.append(f"{call['tool']} missing date/weekday: {call['input']}")
            continue
        try:
            actual = datetime.date.fromisoformat(date_str).strftime("%A")
        except ValueError:
            bad.append(f"{call['tool']} has an unparsable date: {date_str!r}")
            continue
        if actual != weekday:
            bad.append(f"{call['tool']} said {date_str} is a {weekday}, but it's actually a {actual}")
    return (not bad, "ok" if not bad else "; ".join(bad))


def check_forbid_text_patterns(final_text, patterns):
    hits = [p for p in patterns if re.search(p, final_text, re.IGNORECASE)]
    return (not hits, "ok" if not hits else f"reply matched forbidden pattern(s): {hits}")


def check_require_text_patterns(final_text, patterns):
    missing = [p for p in patterns if not re.search(p, final_text, re.IGNORECASE)]
    return (not missing, "ok" if not missing else f"reply is missing required pattern(s): {missing}")


def check_no_fabricated_completion(final_text, tools_used):
    match = COMPLETION_CLAIM_RE.search(final_text)
    if match and not tools_used:
        return (False, f"reply claims completion ({match.group(0)!r}) but no tool was called this turn")
    return (True, "ok")


def check_numbers_grounded_in_tools(final_text, tool_trace):
    mentioned = {int(n) for n in NUMBER_WATT_RE.findall(final_text)}
    if not mentioned:
        return (True, "ok (no wattage numbers in reply)")
    grounded = set()
    for call in tool_trace:
        grounded |= {int(n) for n in re.findall(r"\d+", call["result"])}
    invented = mentioned - grounded
    if invented:
        return (False, f"reply states watt number(s) not seen in any tool result: {sorted(invented)}")
    return (True, "ok")


CHECKS = {
    "expect_tools": lambda case, ctx: check_expect_tools(ctx["tools_used"], case["expect_tools"]),
    "forbid_tools": lambda case, ctx: check_forbid_tools(ctx["tools_used"], case["forbid_tools"]),
    "tool_order": lambda case, ctx: check_tool_order(ctx["tool_trace"], case["tool_order"]),
    "validate_dates": lambda case, ctx: check_dates_match_weekdays(ctx["tool_trace"]),
    "forbid_text_patterns": lambda case, ctx: check_forbid_text_patterns(ctx["final_text"], case["forbid_text_patterns"]),
    "require_text_patterns": lambda case, ctx: check_require_text_patterns(ctx["final_text"], case["require_text_patterns"]),
    "no_fabricated_completion": lambda case, ctx: check_no_fabricated_completion(ctx["final_text"], ctx["tools_used"]),
    "numbers_grounded_in_tools": lambda case, ctx: check_numbers_grounded_in_tools(ctx["final_text"], ctx["tool_trace"]),
}


def resolve_date_placeholder(value, today):
    if not isinstance(value, str) or not value.startswith("@"):
        return value
    key = value[1:]
    if key == "today":
        return today.isoformat()
    if key == "tomorrow":
        return (today + datetime.timedelta(days=1)).isoformat()
    m = re.match(r"in_(\d+)_days", key)
    if m:
        return (today + datetime.timedelta(days=int(m.group(1)))).isoformat()
    m = re.match(r"next_(\w+)", key)
    if m and m.group(1) in WEEKDAYS:
        target = WEEKDAYS.index(m.group(1))
        delta = (target - today.weekday()) % 7 or 7  # "next" = strictly upcoming
        return (today + datetime.timedelta(days=delta)).isoformat()
    raise ValueError(f"unknown date placeholder: {value}")


def apply_setup(setup, today):
    """Create the DB fixtures a case needs. Only ever called against the
    isolated test database the management command sets up — never real data.
    """
    from coach.models import DailyFeeling, Goal, Injury, PlannedSession

    registry = {
        "PlannedSession": PlannedSession,
        "Injury": Injury,
        "Goal": Goal,
        "DailyFeeling": DailyFeeling,
    }
    for item in setup or []:
        model = registry[item["model"]]
        fields = {
            k: resolve_date_placeholder(v, today) for k, v in item["fields"].items()
        }
        model.objects.create(**fields)


def run_case(case, chat_fn):
    """Send every turn in `case` through chat_fn, then run its checks.

    chat_fn must have the same signature as coach.agent.chat. Tool traces
    are read back off the ApiUsage row chat() just wrote — reusing the
    instrumentation built for the usage dashboard instead of duplicating it.
    """
    from coach.models import ApiUsage

    today = datetime.date.today()
    apply_setup(case.get("setup"), today)

    history = []
    tools_used_all = []
    trace_all = []
    final_text = ""
    for message in case["turns"]:
        final_text, tools_used = chat_fn(message, history)
        row = ApiUsage.objects.latest("created_at")
        trace_all.extend(row.tool_trace)
        tools_used_all.extend(tools_used)
        history = history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": final_text},
        ]

    ctx = {"tools_used": tools_used_all, "tool_trace": trace_all, "final_text": final_text}
    # Every CHECKS entry is opt-in per case: a case only runs a check if it
    # sets that key to a truthy value (a non-empty list, or True for a flag).
    results = []
    for key, fn in CHECKS.items():
        if case.get(key):
            ok, detail = fn(case, ctx)
            results.append({"check": key, "ok": ok, "detail": detail})

    return {
        "id": case["id"],
        "passed": all(r["ok"] for r in results),
        "final_text": final_text,
        "tools_used": tools_used_all,
        "checks": results,
    }


def run_all(chat_fn=None, cases=None):
    if chat_fn is None:
        from coach.agent import chat as chat_fn
    cases = cases if cases is not None else load_cases()
    return [run_case(case, chat_fn) for case in cases]
