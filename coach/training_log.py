"""What the athlete actually did: Garmin activities joined with the calendar.

One place that answers "what happened on that day" for the agent's context,
its history tool, the week checker's progression rule, the dashboard and the
activity page:

- a calendar session and a Garmin activity of the same group on the same day
  are ONE entry (a strength activity + the gym session you edited = one gym
  session, with the exercises from the calendar);
- a past calendar session without an activity is `done_manual` when it was
  ticked Completed or edited by hand (gym), otherwise `missed`;
- an activity with no plan is `unplanned`.

Start times are Garmin's local time stored as UTC (TIME_ZONE = 'UTC'), so
`start_time.date()` is the athlete's own date — same as the rest of the app.
"""
import datetime as dt

from coach import athlete_rules
from coach.models import PlannedSession
from sync.models import Activity

# HR zones 1-2 count as easy, 3-5 as hard
EASY_ZONES, HARD_ZONES = (1, 2), (3, 4, 5)


def group_of_activity(activity_type):
    """Garmin activity type -> athlete_rules group, or "other"."""
    t = (activity_type or "").lower()
    if "run" in t:
        return "running"
    if "cycl" in t or "bik" in t or "ride" in t:
        return "cycling"
    if "strength" in t:
        return "gym"
    if "skat" in t:
        return "skating"
    if "tennis" in t:
        return "tennis"
    if "ski" in t:
        return "skiing"
    if "mountaineer" in t or "hik" in t:
        return "mountaineering"
    return "other"


def group_of_plan(activity_type):
    return athlete_rules.group_of(activity_type)


# --- strength --------------------------------------------------------------------

def _garmin_sets_usable(sets):
    """Garmin sends one placeholder set ("Unknown", no reps) when no exercises
    were logged on the watch — that is not a record of the workout."""
    return any((s.get("name") or "").lower() not in ("", "unknown", "unknown exercise")
               and (s.get("reps") or s.get("weight_kg")) for s in sets or [])


def _plan_rows(exercises):
    return [{"name": x["name"], "sets": x.get("sets"), "reps": [x["reps"]] if x.get("reps") else [],
             "weight_kg": x.get("weight_kg")} for x in exercises]


def _plan_exercises(plan):
    return list(plan.exercises.values("name", "sets", "reps", "weight_kg"))


def strength_exercises(activity=None, plan=None):
    """{"source": "garmin"|"planned", "exercises": [{name, sets, reps: [...], weight_kg}],
    "prescribed": [...] | None} or None. Garmin's own sets win when they are real;
    otherwise the calendar session (the athlete's edits) is the record."""
    from coach.dashboard import group_sets
    if activity is not None and _garmin_sets_usable(activity.exercise_sets):
        return {"source": "garmin", "exercises": group_sets(activity.exercise_sets), "prescribed": None}
    if plan is None and activity is not None and activity.start_time:
        plan = (PlannedSession.objects.filter(date=activity.start_time.date(), activity_type__startswith="gym")
                .prefetch_related("exercises").first())
    if plan is None:
        return None
    rows = _plan_exercises(plan)
    if not rows:
        return None
    prescribed = (plan.prescribed or {}).get("exercises")
    return {"source": "planned", "exercises": _plan_rows(rows),
            "prescribed": _plan_rows(prescribed) if prescribed else None}


def exercise_line(row):
    """{"name", "sets", "reps": [...], "weight_kg"} -> "Back squat 4x6 @80kg"."""
    reps = row.get("reps") or []
    if reps and len(set(reps)) == 1:
        rep_txt = str(reps[0])
    elif reps:
        rep_txt = "/".join(str(r) for r in reps)
    else:
        rep_txt = "?"
    sets = row.get("sets") or (len(reps) if reps else None)
    txt = f"{row['name']} {sets}x{rep_txt}" if sets else f"{row['name']} x{rep_txt}"
    if row.get("weight_kg"):
        txt += f" @{row['weight_kg']:g}kg"
    return txt


# --- entries ---------------------------------------------------------------------

def _zone_minutes(a, zones):
    secs = [getattr(a, f"hr_zone_{z}_seconds") or 0 for z in zones]
    return round(sum(secs) / 60)


def _pace(a):
    if not a.distance_meters or not a.duration_seconds:
        return None
    sec = a.duration_seconds / (a.distance_meters / 1000)
    return f"{int(sec // 60)}:{int(sec % 60):02d}/km"


def _round(v, n=0):
    if v is None:
        return None
    return round(v) if n == 0 else round(v, n)


def activity_fields(a):
    group = group_of_activity(a.activity_type)
    has_zones = any(getattr(a, f"hr_zone_{z}_seconds") for z in range(1, 6))
    row = {
        "date": a.start_time.date().isoformat(),
        "type": a.activity_type,
        "group": group,
        "minutes": _round((a.duration_seconds or 0) / 60),
        "km": _round(a.distance_meters / 1000, 1) if a.distance_meters else None,
        "pace": _pace(a) if group == "running" else None,
        "elev_gain_m": _round(a.elevation_gain_m) if a.elevation_gain_m else None,
        "avg_hr": a.avg_hr,
        "easy_min": _zone_minutes(a, EASY_ZONES) if has_zones else None,
        "hard_min": _zone_minutes(a, HARD_ZONES) if has_zones else None,
        "load": _round(a.training_load),
        "effect": a.training_effect_label,
        "tss": _round(a.tss),
        "avg_power": a.avg_power,
        "norm_power": a.normalized_power,
    }
    return row


def _planned_fields(p):
    return {k: v for k, v in {
        "title": p.title or p.activity_type, "activity_type": p.activity_type,
        "minutes": p.duration_minutes, "intensity": p.intensity or None,
    }.items() if v}


def _manual_done(p):
    return p.completed or (group_of_plan(p.activity_type) == "gym" and p.prescribed is not None)


def entries(start, end, today=None):
    """Every training entry from start to end (dates, inclusive), oldest first.
    Each: activity fields (when there is an activity) + "planned" + "status"
    + "exercises" for gym. Internal keys start with "_" (the model objects)."""
    today = today or dt.date.today()
    acts = list(Activity.objects.filter(start_time__date__gte=start, start_time__date__lte=end)
                .exclude(start_time__isnull=True).order_by("start_time"))
    plans = list(PlannedSession.objects.filter(date__gte=start, date__lte=end).exclude(activity_type="rest")
                 .prefetch_related("exercises").order_by("date", "id"))

    out = []
    used = set()
    for a in acts:
        day, group = a.start_time.date(), group_of_activity(a.activity_type)
        plan = next((p for p in plans if p.id not in used and p.date == day
                     and group != "other" and group_of_plan(p.activity_type) == group), None)
        if plan:
            used.add(plan.id)
        e = activity_fields(a)
        e["status"] = "done" if plan else "unplanned"
        if plan:
            e["planned"] = _planned_fields(plan)
        e["_activity"], e["_plan"] = a, plan
        out.append(e)

    for p in plans:
        if p.id in used or p.date > today:
            continue
        group = group_of_plan(p.activity_type)
        if _manual_done(p):
            status = "done_manual"
        elif p.date == today:
            status = "today"
        else:
            status = "missed"
        out.append({"date": p.date.isoformat(), "type": p.activity_type, "group": group,
                    "minutes": p.duration_minutes if status == "done_manual" else None,
                    "planned": _planned_fields(p), "status": status, "_activity": None, "_plan": p})

    for e in out:
        if e["group"] == "gym" and e["status"] in ("done", "done_manual", "unplanned"):
            st = strength_exercises(e["_activity"], e["_plan"]) if e["_plan"] or e["_activity"] else None
            if st:
                e["exercises"] = [exercise_line(r) for r in st["exercises"]]
                e["exercises_source"] = st["source"]
                if st["prescribed"]:
                    prescribed = [exercise_line(r) for r in st["prescribed"]]
                    if prescribed != e["exercises"]:
                        e["prescribed"] = prescribed
    out.sort(key=lambda e: e["date"])
    return out


def public(e):
    """An entry without internal keys and empty values — what the model sees."""
    return {k: v for k, v in e.items() if not k.startswith("_") and v not in (None, [], {}, "")}


def recent_log(days=14, today=None):
    """The last `days` days, newest first."""
    today = today or dt.date.today()
    return [public(e) for e in reversed(entries(today - dt.timedelta(days=days - 1), today, today))]


# --- weeks -----------------------------------------------------------------------

def _monday(d):
    return d - dt.timedelta(days=d.weekday())


def weekly_summary(weeks=8, today=None):
    """[{"week": monday, "partial": bool, "groups": {group: totals}}], oldest first.
    Counts what was done: activities and calendar sessions marked done by hand."""
    today = today or dt.date.today()
    first = _monday(today) - dt.timedelta(weeks=weeks - 1)
    rows = {first + dt.timedelta(weeks=i): {} for i in range(weeks)}
    for e in entries(first, today, today):
        if e["status"] not in ("done", "done_manual", "unplanned"):
            continue
        week = rows[_monday(dt.date.fromisoformat(e["date"]))]
        g = week.setdefault(e["group"], {"sessions": 0, "minutes": 0, "km": 0.0, "elev_gain_m": 0,
                                         "load": 0, "longest_min": 0, "hard_min": 0})
        g["sessions"] += 1
        g["minutes"] += e.get("minutes") or 0
        g["km"] = round(g["km"] + (e.get("km") or 0), 1)
        g["elev_gain_m"] += e.get("elev_gain_m") or 0
        g["load"] += e.get("load") or 0
        g["longest_min"] = max(g["longest_min"], e.get("minutes") or 0)
        g["hard_min"] += e.get("hard_min") or 0
    out = []
    for monday, groups in rows.items():
        clean = {name: {k: v for k, v in g.items() if v} for name, g in groups.items()}
        out.append({"week": monday.isoformat(), "partial": monday == _monday(today), "groups": clean})
    return out


def baseline_minutes(weeks=4, today=None):
    """{group: average weekly minutes over the last `weeks` COMPLETE weeks}.
    Empty when fewer than 2 of those weeks have any training — too little to
    judge a jump against."""
    summary = weekly_summary(weeks + 1, today)[:-1]   # drop the current, partial week
    if sum(1 for w in summary if w["groups"]) < 2:
        return {}
    totals = {}
    for w in summary:
        for group, g in w["groups"].items():
            totals[group] = totals.get(group, 0) + g.get("minutes", 0)
    return {group: round(total / weeks) for group, total in totals.items() if group != "other" and total}


# --- history tool ----------------------------------------------------------------

def exercise_history(name, weeks=8, today=None):
    """Every done gym session in the window that has this exercise (case-insensitive
    substring), oldest first: date, what was done, what was prescribed."""
    today = today or dt.date.today()
    needle = name.strip().lower()
    out = []
    for e in entries(today - dt.timedelta(weeks=weeks), today, today):
        if e["group"] != "gym" or not e.get("exercises"):
            continue
        done = [x for x in e["exercises"] if needle in x.lower()]
        if done:
            row = {"date": e["date"], "done": done}
            presc = [x for x in e.get("prescribed", []) if needle in x.lower()]
            if presc:
                row["prescribed"] = presc
            out.append(row)
    return out


def sport_history(group, weeks=8, today=None):
    today = today or dt.date.today()
    return [public(e) for e in entries(today - dt.timedelta(weeks=weeks), today, today) if e["group"] == group]
