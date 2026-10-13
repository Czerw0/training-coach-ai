"""Stats page data: one JSON payload for a chosen period (?days=N). Read-only.
Everything is computed from synced Garmin data and the planner — no model calls."""
import datetime as dt
import math
import statistics
from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from coach.models import DailyFeeling, Goal, Injury, PlannedSession
from sync.models import Activity, DailyStats, FTPRecord, HRVRecord, SleepRecord

PERIODS = (28, 84, 182, 365)
ZONES = range(1, 6)


def _monday(d):
    return d - dt.timedelta(days=d.weekday())


def _totals(rows):
    return {
        "sessions": len(rows),
        "hours": round(sum((r["duration_seconds"] or 0) for r in rows) / 3600, 1),
        "km": round(sum((r["distance_meters"] or 0) for r in rows) / 1000),
        "load": round(sum((r["training_load"] or 0) for r in rows)),
    }


def _activities(start, end):
    return list(Activity.objects.filter(start_time__date__gte=start, start_time__date__lte=end).values(
        "id", "start_time", "activity_type", "activity_name", "duration_seconds", "distance_meters",
        "training_load", "avg_hr", *[f"hr_zone_{z}_seconds" for z in ZONES]))


def daily_load(start, end):
    out = defaultdict(float)
    for a in Activity.objects.filter(start_time__date__gte=start, start_time__date__lte=end).values("start_time", "training_load"):
        out[a["start_time"].date()] += a["training_load"] or 0
    return out


def fitness_series(start, end):
    """CTL (42-day) / ATL (7-day) exponentially weighted load and TSB = CTL - ATL,
    warmed up over the 84 days before `start`."""
    warm = start - dt.timedelta(days=84)
    loads = daily_load(warm, end)
    ctl = atl = 0.0
    k_ctl, k_atl = 1 - math.exp(-1 / 42), 1 - math.exp(-1 / 7)
    out, d = [], warm
    while d <= end:
        load = loads.get(d, 0)
        ctl += (load - ctl) * k_ctl
        atl += (load - atl) * k_atl
        if d >= start:
            out.append({"date": d.isoformat(), "ctl": round(ctl, 1), "atl": round(atl, 1), "tsb": round(ctl - atl, 1)})
        d += dt.timedelta(days=1)
    return out


def _mean(xs):
    return statistics.mean(xs) if xs else None


def _more_less(diff, unit):
    if diff == 0:
        return "about the same"
    return f"{abs(diff)}{unit} {'higher' if diff > 0 else 'lower'}"


def correlations(start, end):
    """Plain comparisons between groups of days. Only reported with >= 5 days per group."""
    out = []
    hrv = {h.date: h.hrv_rmssd for h in HRVRecord.objects.filter(date__gte=start, date__lte=end + dt.timedelta(days=1)) if h.hrv_rmssd}
    loads = daily_load(start, end)
    trained = [v for v in loads.values() if v > 0]

    if len(trained) >= 8 and hrv:
        cut = statistics.quantiles(trained, n=4)[2]
        after_hard, after_other = [], []
        d = start
        while d <= end:
            nxt = hrv.get(d + dt.timedelta(days=1))
            if nxt:
                (after_hard if loads.get(d, 0) >= cut else after_other).append(nxt)
            d += dt.timedelta(days=1)
        if len(after_hard) >= 5 and len(after_other) >= 5:
            a, b = _mean(after_hard), _mean(after_other)
            diff = round((a - b) / b * 100)
            out.append({"title": f"HRV after your hardest days: {_more_less(diff, '%')} than after other days",
                        "text": f"{round(a)} ms after your top-25% load days vs {round(b)} ms after the rest "
                                f"({len(after_hard)} vs {len(after_other)} mornings)."})

        after_rest, after_train = [], []
        d = start
        while d <= end:
            nxt = hrv.get(d + dt.timedelta(days=1))
            if nxt:
                (after_train if loads.get(d, 0) > 0 else after_rest).append(nxt)
            d += dt.timedelta(days=1)
        if len(after_rest) >= 5 and len(after_train) >= 5:
            a, b = _mean(after_rest), _mean(after_train)
            out.append({"title": f"HRV after a rest day: {_more_less(round(a - b), ' ms')} than after training",
                        "text": f"{round(a)} ms after a rest day vs {round(b)} ms after a training day."})

    sleep = {s.date: s.score for s in SleepRecord.objects.filter(date__gte=start, date__lte=end) if s.score is not None}
    poor = [hrv[d] for d, s in sleep.items() if s < 60 and d in hrv]
    good = [hrv[d] for d, s in sleep.items() if s >= 75 and d in hrv]
    if len(poor) >= 5 and len(good) >= 5:
        a, b = _mean(poor), _mean(good)
        out.append({"title": f"HRV after a poor night: {_more_less(round(a - b), ' ms')} than after a good one",
                    "text": f"Mornings after a sleep score under 60 average {round(a)} ms, after 75+ they average {round(b)} ms."})

    days = defaultdict(int)
    for a in Activity.objects.filter(start_time__date__gte=start, start_time__date__lte=end).values("start_time"):
        days[a["start_time"].strftime("%A")] += 1
    if sum(days.values()) >= 8:
        top = max(days, key=days.get)
        out.append({"title": f"{top} is your most consistent training day",
                    "text": f"{days[top]} sessions on a {top} in this period."})
    return out


def records(rows, weeks):
    out = []
    if rows:
        longest = max(rows, key=lambda r: r["duration_seconds"] or 0)
        if longest["duration_seconds"]:
            out.append({"label": "Longest session", "id": longest.get("id"), "value": f"{round(longest['duration_seconds'] / 60)} min",
                        "sub": f"{longest['activity_name'] or longest['activity_type']} · {longest['start_time'].date().isoformat()}"})
        furthest = max(rows, key=lambda r: r["distance_meters"] or 0)
        if furthest["distance_meters"]:
            out.append({"label": "Longest distance", "id": furthest.get("id"), "value": f"{furthest['distance_meters'] / 1000:.1f} km",
                        "sub": f"{furthest['activity_name'] or furthest['activity_type']} · {furthest['start_time'].date().isoformat()}"})
        hardest = max(rows, key=lambda r: r["training_load"] or 0)
        if hardest["training_load"]:
            out.append({"label": "Hardest session", "id": hardest.get("id"), "value": f"load {round(hardest['training_load'])}",
                        "sub": f"{hardest['activity_name'] or hardest['activity_type']} · {hardest['start_time'].date().isoformat()}"})
    if weeks:
        big = max(weeks, key=lambda w: w["hours"])
        if big["hours"]:
            out.append({"label": "Biggest week", "value": f"{big['hours']} h", "sub": f"week of {big['week_start']}"})
    return out


def _adherence(today, start):
    past = PlannedSession.objects.filter(date__lt=today).exclude(activity_type="rest").order_by("-date")
    activity_dates = set(Activity.objects.filter(start_time__date__lt=today).values_list("start_time__date", flat=True))
    matched, missed = 0, []
    by_type = defaultdict(lambda: {"planned": 0, "done": 0})
    for s in past:
        hit = s.date in activity_dates
        matched += hit
        if s.date >= start:
            by_type[s.activity_type]["planned"] += 1
            by_type[s.activity_type]["done"] += hit
        if not hit and len(missed) < 10:
            missed.append({"date": s.date.isoformat(), "title": s.title or s.activity_type, "activity_type": s.activity_type})
    total = past.count()
    return {
        "matched": matched, "total": total,
        "rate": round(matched / total * 100) if total else None,
        "missed": missed,
        "by_type": [{"activity_type": k, **v} for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]["planned"])],
    }


def feel_stats(start, end):
    """Soreness / energy / motivation series, most-reported sore areas, and
    next-day soreness after the hardest training days vs the rest."""
    rows = list(DailyFeeling.objects.filter(date__gte=start, date__lte=end).order_by("date"))
    series = [{"date": f.date.isoformat(), "soreness": f.muscle_soreness, "energy": f.energy_level,
               "motivation": f.motivation} for f in rows]
    parts = defaultdict(int)
    for f in rows:
        for part in (f.muscle_sore or "").split(","):
            if part.strip():
                parts[part.strip().replace("_", " ").title()] += 1
    soreness = {f.date: f.muscle_soreness for f in rows if f.muscle_soreness is not None}
    after_hard = None
    loads = daily_load(start, end)
    trained = [v for v in loads.values() if v > 0]
    if len(trained) >= 8:
        cut = statistics.quantiles(trained, n=4)[2]
        hard, other = [], []
        for d, s in soreness.items():
            (hard if loads.get(d - dt.timedelta(days=1), 0) >= cut else other).append(s)
        if len(hard) >= 5 and len(other) >= 5:
            after_hard = {"hard": round(_mean(hard), 1), "other": round(_mean(other), 1), "n_hard": len(hard), "n_other": len(other)}
    avg = lambda k: round(_mean([r[k] for r in series if r[k] is not None]), 1) if any(r[k] is not None for r in series) else None
    return {"series": series, "days_logged": len(rows), "avg": {k: avg(k) for k in ("soreness", "energy", "motivation")},
            "parts": [{"part": k, "n": v} for k, v in sorted(parts.items(), key=lambda kv: -kv[1])][:8],
            "after_hard": after_hard}


def injury_list(today):
    """Every injury active at some point in the last 12 months. Stats are
    computed in the browser so injuries hidden from view drop out of them too."""
    since = today - dt.timedelta(days=365)
    return [{"id": i.id, "body_part": (i.body_part or "Injury").title(), "severity": i.severity,
             "start": i.date_started.isoformat(), "end": i.date_resolved.isoformat() if i.date_resolved else None,
             "days": ((i.date_resolved or today) - i.date_started).days}
            for i in Injury.objects.filter(date_started__lte=today).exclude(date_resolved__lt=since).order_by("date_started")]


@login_required
@require_http_methods(["GET"])
def stats_data(request):
    today = dt.date.today()
    try:
        days = int(request.GET.get("days", 84))
    except ValueError:
        days = 84
    if days not in PERIODS:
        days = 84
    start = today - dt.timedelta(days=days - 1)
    prev_start = start - dt.timedelta(days=days)

    rows = _activities(start, today)
    prev_rows = _activities(prev_start, start - dt.timedelta(days=1))

    first = Activity.objects.order_by("start_time").first()
    summary = {
        "total_activities": Activity.objects.count(),
        "first_activity_date": first.start_time.date().isoformat() if first else None,
        "active_goals": Goal.objects.filter(is_active=True).count(),
        "active_injuries": Injury.objects.filter(date_resolved__isnull=True).count(),
    }

    # by type, fixed 90 days (kept for compatibility) and for the period
    by_type_90d = list(Activity.objects.filter(start_time__date__gte=today - dt.timedelta(days=90))
                       .values("activity_type").annotate(n=Count("id"), minutes=Sum("duration_seconds")).order_by("-n"))
    for r in by_type_90d:
        r["minutes"] = round((r["minutes"] or 0) / 60)

    types = defaultdict(lambda: {"n": 0, "minutes": 0, "km": 0, "hr": []})
    for r in rows:
        t = types[r["activity_type"] or "other"]
        t["n"] += 1
        t["minutes"] += (r["duration_seconds"] or 0) / 60
        t["km"] += (r["distance_meters"] or 0) / 1000
        if r["avg_hr"]:
            t["hr"].append(r["avg_hr"])
    by_type = [{"activity_type": k, "n": v["n"], "minutes": round(v["minutes"]), "km": round(v["km"], 1),
                "avg_hr": round(_mean(v["hr"])) if v["hr"] else None}
               for k, v in sorted(types.items(), key=lambda kv: -kv[1]["minutes"])]

    # weekly buckets over the period: hours per type, zones, count
    first_week = _monday(start)
    week_keys = []
    w = first_week
    while w <= today:
        week_keys.append(w.isoformat())
        w += dt.timedelta(weeks=1)
    weekly = {k: {"week_start": k, "hours": 0.0, "count": 0, "load": 0.0, "by_type": defaultdict(float),
                  "zones": [0.0] * 5} for k in week_keys}
    for r in rows:
        b = weekly[_monday(r["start_time"].date()).isoformat()]
        hours = (r["duration_seconds"] or 0) / 3600
        b["hours"] += hours
        b["count"] += 1
        b["load"] += r["training_load"] or 0
        b["by_type"][r["activity_type"] or "other"] += hours
        for i, z in enumerate(ZONES):
            b["zones"][i] += (r[f"hr_zone_{z}_seconds"] or 0) / 60
    weeks = [{"week_start": k, "hours": round(v["hours"], 1), "count": v["count"], "load": round(v["load"]),
              "by_type": {t: round(h, 2) for t, h in v["by_type"].items()},
              "zones": [round(m) for m in v["zones"]]} for k, v in weekly.items()]

    zone_tot = [sum(w["zones"][i] for w in weeks) for i in range(5)]
    zt = sum(zone_tot) or 1
    intensity = {"low": round((zone_tot[0] + zone_tot[1]) / zt * 100), "mid": round(zone_tot[2] / zt * 100),
                 "high": round((zone_tot[3] + zone_tot[4]) / zt * 100), "zone_minutes": [round(m) for m in zone_tot]}

    # legacy 12-week minutes series
    since_12w = today - dt.timedelta(weeks=12)
    legacy = defaultdict(lambda: {"count": 0, "minutes": 0})
    for a in Activity.objects.filter(start_time__date__gte=since_12w).values("start_time", "duration_seconds"):
        k = _monday(a["start_time"].date()).isoformat()
        legacy[k]["count"] += 1
        legacy[k]["minutes"] += round((a["duration_seconds"] or 0) / 60)
    weekly_volume = [{"week_start": k, **v} for k, v in sorted(legacy.items())]

    hrv = {h["date"]: h for h in HRVRecord.objects.filter(date__gte=start).values("date", "hrv_rmssd", "resting_hr")}
    sleep = {s["date"]: s for s in SleepRecord.objects.filter(date__gte=start).values("date", "score", "duration_hours")}
    stats = {s["date"]: s for s in DailyStats.objects.filter(date__gte=start).values(
        "date", "body_battery_high", "vo2max_running", "vo2max_cycling", "stress_level_avg")}
    recovery, d = [], start
    while d <= today:
        h, s, st = hrv.get(d, {}), sleep.get(d, {}), stats.get(d, {})
        recovery.append({"date": d.isoformat(), "hrv": h.get("hrv_rmssd"), "rhr": h.get("resting_hr"),
                         "sleep_score": s.get("score"), "sleep_hours": s.get("duration_hours"),
                         "body_battery": st.get("body_battery_high"), "stress": st.get("stress_level_avg"),
                         "vo2_run": st.get("vo2max_running"), "vo2_bike": st.get("vo2max_cycling")})
        d += dt.timedelta(days=1)

    heat_start = _monday(today) - dt.timedelta(weeks=25)
    loads = daily_load(heat_start, today)
    heatmap = [{"date": (heat_start + dt.timedelta(days=i)).isoformat(),
                "load": round(loads.get(heat_start + dt.timedelta(days=i), 0))}
               for i in range((today - heat_start).days + 1)]

    return JsonResponse({
        "summary": summary,
        "period": {"days": days, "start": start.isoformat(), "end": today.isoformat(), "options": list(PERIODS)},
        "totals": _totals(rows), "prev_totals": _totals(prev_rows),
        "by_type_90d": by_type_90d,
        "by_type": by_type,
        "weekly_volume": weekly_volume,
        "weeks": weeks,
        "intensity": intensity,
        "fitness": fitness_series(start, today),
        "recovery": recovery,
        "ftp": [{"date": f.date.isoformat(), "watts": f.ftp_watts} for f in FTPRecord.objects.order_by("date")],
        "heatmap": heatmap,
        "records": records(rows, weeks),
        "correlations": correlations(start, today),
        "adherence": _adherence(today, start),
        "feel": feel_stats(start, today),
        "injuries": injury_list(today),
        "injury_window": {"start": (today - dt.timedelta(days=365)).isoformat(), "end": today.isoformat()},
    })
