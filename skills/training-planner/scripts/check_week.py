#!/usr/bin/env python3
"""Deterministic constraint checker for a candidate training week.

This is the payoff of putting scheduling metadata in frontmatter: the rules run
in Python, not in the model's head, so a persuasive prompt can't argue the plan
out of a hard constraint. Run this on a draft week BEFORE writing it up; fix
every `error`, and either fix or explicitly state every `warning`.

Input — a JSON array of planned sessions (file path, or stdin):

    [
      {"id": "gym/lower-eccentric", "start": "2026-08-10T07:00"},
      {"id": "running/intervals",   "start": "2026-08-12T18:00"},
      {"id": "cycling/endurance",   "start": "2026-08-13T09:00"}
    ]

`start` is ISO-8601. `id` is "category/skill"; `session` is accepted as an alias.

Output — JSON (default) or `--format text`. Exit code is non-zero if any
`error`-severity violation is found, so this doubles as a CI-style gate.

    python check_week.py week.json
    python check_week.py week.json --format text
    cat week.json | python check_week.py -

--- Design decisions (the ones the original stub left open) ---

1. Direction. Real spacing is directional (eccentric-then-intervals is worse
   than the reverse) but `spacing_h` is declared symmetric. We enforce it
   symmetrically as a minimum start-to-start gap in either order. A directional
   `spacing_before_h` field could refine this later; the symmetric floor is the
   safe under-approximation.
2. Disagreement. Both files in a pair may declare a gap, and the numbers may
   differ. The STRICTER (max) wins — a checker should never be the reason a
   real constraint got relaxed.
3. Axis saturation. none/low/moderate/high map to 0/1/2/3. Each axis is summed
   over a rolling window equal to ITS OWN documented residue (load-and-recovery
   §1): neural 48 h, mechanical 72 h, damage 72 h. mechanical and neural are the
   injury/freshness axes, so a windowed sum >=6 (two 'high') is an error and ==5
   a warning; damage stacking (>=5) is a warning (DOMS); metabolic clears fast
   enough to ignore.
4. Severity. `error` = the plan is wrong, fix it. `warning` = a defensible
   compromise the model must state in the plan rather than bury.
"""
import json
import sys
from datetime import datetime, timedelta

from frontmatter import load_session_meta, use_utf8_stdout

_AXIS_SCORE = {"none": 0, "low": 1, "moderate": 2, "high": 3, "": 0}
# For saturation, 'low' filler contributes nothing — load-and-recovery §1 is
# explicit that low-cost work (easy Z2) stacks densely and shouldn't count
# toward overloading an axis. Only moderate/high exposures accumulate.
_SAT_SCORE = {"none": 0, "low": 0, "moderate": 2, "high": 3, "": 0}
# Each axis is saturated over its own residue window (load-and-recovery §1).
_SATURATION_WINDOW_H = {"mechanical": 72, "neural": 48, "damage": 72}
_SAME_DAY_MIN_GAP_H = 6      # planning-the-week §3: same-day pair needs >=6 h
_HARD_AXES = ("neural", "mechanical", "metabolic", "damage")


def _load_week(source):
    raw = sys.stdin.read() if source in ("-", None) else open(source, encoding="utf-8").read()
    data = json.loads(raw)
    sessions = []
    for i, item in enumerate(data):
        sid = item.get("id") or item.get("session")
        start = item.get("start")
        if not sid or not start:
            raise ValueError(f"session #{i} needs both 'id' and 'start'")
        sessions.append({"id": sid, "start": datetime.fromisoformat(start)})
    sessions.sort(key=lambda s: s["start"])
    return sessions


def _axis_val(meta, axis):
    return _AXIS_SCORE.get(str((meta.get("load") or {}).get(axis, "")).strip(), 0)


def _sat_val(meta, axis):
    return _SAT_SCORE.get(str((meta.get("load") or {}).get(axis, "")).strip(), 0)


def _is_hard(meta):
    """A session with any single high axis, or >=48 h residual, is 'hard'."""
    if any(_axis_val(meta, a) >= 3 for a in _HARD_AXES):
        return True
    try:
        return int(meta.get("residual_fatigue_h", 0)) >= 48
    except (ValueError, TypeError):
        return False


def _required_spacing(a_meta, b_meta, a_id, b_id):
    """Stricter of the gap each file declares toward the other; None if neither."""
    vals = []
    for meta, other in ((a_meta, b_id), (b_meta, a_id)):
        h = (meta.get("spacing_h") or {}).get(other)
        if isinstance(h, int):
            vals.append(h)
    return max(vals) if vals else None


def check(sessions):
    violations = []
    metas = {}
    for s in sessions:
        m = load_session_meta(s["id"])
        if m is None:
            violations.append({
                "kind": "unknown-session", "severity": "warning",
                "session": s["id"],
                "message": f"No reference file for '{s['id']}' — cannot fully check it.",
            })
        metas[s["id"]] = m or {}

    # --- pairwise checks -----------------------------------------------------
    for i in range(len(sessions)):
        for j in range(i + 1, len(sessions)):
            a, b = sessions[i], sessions[j]
            am, bm = metas[a["id"]], metas[b["id"]]
            gap_h = (b["start"] - a["start"]).total_seconds() / 3600.0

            # 1. same-day conflicts
            same_day = a["start"].date() == b["start"].date()
            conflict = (b["id"] in am.get("same_day_conflicts", [])
                        or a["id"] in bm.get("same_day_conflicts", []))
            if same_day and conflict:
                if gap_h < _SAME_DAY_MIN_GAP_H:
                    violations.append({
                        "kind": "same-day-conflict", "severity": "error",
                        "a": a["id"], "b": b["id"], "gap_h": round(gap_h, 1),
                        "message": (f"{a['id']} and {b['id']} conflict on the same day "
                                    f"and are only {gap_h:.1f} h apart (<{_SAME_DAY_MIN_GAP_H} h)."),
                    })
                else:
                    violations.append({
                        "kind": "same-day-conflict", "severity": "warning",
                        "a": a["id"], "b": b["id"], "gap_h": round(gap_h, 1),
                        "message": (f"{a['id']} and {b['id']} are listed as same-day conflicts. "
                                    f"{gap_h:.1f} h apart is workable only if the priority session "
                                    "goes first and the other is kept clearly sub-maximal — state it."),
                    })

            # 2. spacing (start-to-start, symmetric floor)
            required = _required_spacing(am, bm, a["id"], b["id"])
            if required is not None and gap_h < required:
                violations.append({
                    "kind": "spacing", "severity": "error",
                    "a": a["id"], "b": b["id"],
                    "required_h": required, "actual_h": round(gap_h, 1),
                    "message": (f"{a['id']} -> {b['id']} are {gap_h:.1f} h apart; "
                                f"{required} h required."),
                })

            # 4. day-after protection: hard-on-hard within 24 h, not already
            #    flagged by an explicit spacing rule above
            if required is None and 0 < gap_h <= 24 and _is_hard(am) and _is_hard(bm):
                violations.append({
                    "kind": "day-after", "severity": "warning",
                    "a": a["id"], "b": b["id"], "gap_h": round(gap_h, 1),
                    "message": (f"{b['id']} is {gap_h:.1f} h after the hard session {a['id']}; "
                                "the day after a hard session should be genuinely easy."),
                })

    # 3. axis saturation — each axis over a rolling window of its own residue.
    #    Overlapping windows produce nested findings; keep only the single worst
    #    window per axis so the report carries one line per genuinely loaded axis.
    for axis, window_h in _SATURATION_WINDOW_H.items():
        worst = None
        for i, anchor in enumerate(sessions):
            window_end = anchor["start"] + timedelta(hours=window_h)
            window = [s for s in sessions[i:] if s["start"] < window_end]
            if len(window) < 2:
                continue
            total = sum(_sat_val(metas[s["id"]], axis) for s in window)
            if axis in ("mechanical", "neural"):
                sev = "error" if total >= 6 else "warning" if total == 5 else None
            else:  # damage: DOMS stacking is a warning, never a hard error
                sev = "warning" if total >= 5 else None
            if sev is None:
                continue
            cand = (total, sev, anchor["start"], window_h, [s["id"] for s in window])
            if worst is None or total > worst[0]:
                worst = cand
        if worst:
            total, sev, start, w_h, ids = worst
            violations.append({
                "kind": "axis-saturation", "severity": sev, "axis": axis,
                "window_start": start.isoformat(), "window_h": w_h,
                "load_sum": total, "sessions": ids,
                "message": (f"{axis} load sums to {total} across {len(ids)} sessions in {w_h} h "
                            f"({', '.join(ids)}) — the pattern that overloads that axis."),
            })

    # dedup identical saturation windows (overlapping anchors can repeat)
    seen, deduped = set(), []
    for v in violations:
        key = json.dumps(v, sort_keys=True, default=str)
        if key not in seen:
            seen.add(key)
            deduped.append(v)
    order = {"error": 0, "warning": 1}
    deduped.sort(key=lambda v: order.get(v["severity"], 2))
    return deduped


def _format_text(violations):
    if not violations:
        return "OK — no constraint violations."
    lines = []
    for v in violations:
        lines.append(f"[{v['severity'].upper():7}] {v['kind']}: {v['message']}")
    n_err = sum(v["severity"] == "error" for v in violations)
    n_warn = sum(v["severity"] == "warning" for v in violations)
    lines.append(f"\n{n_err} error(s), {n_warn} warning(s).")
    return "\n".join(lines)


def main(argv):
    use_utf8_stdout()
    args = [a for a in argv if not a.startswith("--")]
    text = "--format" in argv and "text" in argv
    source = args[0] if args else "-"
    try:
        sessions = _load_week(source)
    except (ValueError, json.JSONDecodeError, OSError) as e:
        print(f"input error: {e}", file=sys.stderr)
        return 2
    violations = check(sessions)
    print(_format_text(violations) if text else json.dumps(violations, indent=2, default=str))
    return 1 if any(v["severity"] == "error" for v in violations) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
