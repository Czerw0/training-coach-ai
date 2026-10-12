"""Today page: one JSON payload with readiness, today's sessions, the week,
recovery trends, load and rule-based insights. Read-only."""
import datetime as dt

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from coach import metrics
from coach.models import PlannedSession
from sync.models import Activity, DailyStats, FTPRecord, HRVRecord, SleepRecord, UserProfile

ZONES = range(1, 6)


def _session_dict(s):
    return {
        "id": s.id, "date": s.date.isoformat(), "activity_type": s.activity_type,
        "title": s.title or s.activity_type.replace("_", " ").title(),
        "description": s.description, "duration_minutes": s.duration_minutes,
        "intensity": s.intensity, "completed": s.completed, "created_by": s.created_by,
        "exercises": list(s.exercises.values("name", "sets", "reps", "weight_kg", "notes")),
    }


def _week(today):
    monday = today - dt.timedelta(days=today.weekday())
    days = [monday + dt.timedelta(days=i) for i in range(7)]
    planned = PlannedSession.objects.filter(date__range=(days[0], days[-1])).exclude(activity_type="rest")
    done = Activity.objects.filter(start_time__date__range=(days[0], days[-1])).values("start_time", "activity_type")
    out = []
    for d in days:
        out.append({
            "date": d.isoformat(), "weekday": d.strftime("%a"), "day": d.day, "is_today": d == today,
            "planned": [{"type": p.activity_type, "title": p.title or p.activity_type} for p in planned if p.date == d],
            "done": [a["activity_type"] for a in done if a["start_time"].date() == d],
        })
    return out


def _weekly_load(today, weeks=8):
    monday = today - dt.timedelta(days=today.weekday())
    start = monday - dt.timedelta(weeks=weeks - 1)
    rows = Activity.objects.filter(start_time__date__gte=start).values("start_time", "training_load")
    buckets = {(start + dt.timedelta(weeks=i)).isoformat(): 0 for i in range(weeks)}
    for r in rows:
        d = r["start_time"].date()
        key = (d - dt.timedelta(days=d.weekday())).isoformat()
        if key in buckets:
            buckets[key] += r["training_load"] or 0
    return [{"week_start": k, "load": round(v)} for k, v in buckets.items()]


def group_sets(sets):
    """Consecutive sets of the same exercise -> one row: sets, reps per set, top weight."""
    rows = []
    for s in sets:
        if rows and rows[-1]["name"] == s["name"]:
            row = rows[-1]
        else:
            row = {"name": s["name"], "sets": 0, "reps": [], "weight_kg": None}
            rows.append(row)
        row["sets"] += 1
        if s.get("reps") is not None:
            row["reps"].append(s["reps"])
        if s.get("weight_kg") is not None:
            row["weight_kg"] = max(row["weight_kg"] or 0, s["weight_kg"])
    return rows


def _latest_activity():
    a = Activity.objects.exclude(start_time__isnull=True).order_by("-start_time").first()
    if not a:
        return None
    zones = [getattr(a, f"hr_zone_{z}_seconds") or 0 for z in ZONES]
    strength = None
    if "strength" in (a.activity_type or ""):
        strength = {"total_sets": a.active_sets or a.total_sets, "total_reps": a.total_reps,
                    "source": None, "exercises": []}
        if a.exercise_sets:
            strength["source"] = "garmin"
            strength["exercises"] = group_sets(a.exercise_sets)
        else:
            plan = (PlannedSession.objects.filter(date=a.start_time.date(), activity_type__startswith="gym")
                    .prefetch_related("exercises").first())
            if plan:
                strength["source"] = "planned"
                strength["exercises"] = [
                    {"name": x.name, "sets": x.sets, "reps": [x.reps] if x.reps else [], "weight_kg": x.weight_kg}
                    for x in plan.exercises.all()]
    return {
        "strength": strength,
        "date": a.start_time.date().isoformat(), "name": a.activity_name or a.activity_type,
        "type": a.activity_type,
        "minutes": round(a.duration_seconds / 60) if a.duration_seconds else None,
        "km": round(a.distance_meters / 1000, 1) if a.distance_meters else None,
        "avg_hr": a.avg_hr, "load": round(a.training_load) if a.training_load else None,
        "tss": round(a.tss) if a.tss else None,
        "zone_minutes": [round(s / 60) for s in zones] if any(zones) else None,
    }


def build_insights(today, hrv_today, baseline, ratio, week):
    """Rule-based observations, most important first. No model call."""
    out = []
    mean, sd = baseline
    if hrv_today is not None and mean and sd and hrv_today < mean - sd:
        out.append({"level": "warn", "title": f"HRV {round(hrv_today)} ms, below your normal range",
                    "text": f"Your 28-day baseline is {round(mean)} ± {round(sd)} ms. Keep today's intensity controlled."})
    low_hrv_days = HRVRecord.objects.filter(date__gt=today - dt.timedelta(days=3), date__lte=today,
                                            hrv_rmssd__isnull=False)
    if mean and low_hrv_days.count() == 3 and all(h.hrv_rmssd < mean for h in low_hrv_days):
        out.append({"level": "warn", "title": "HRV below average three days running",
                    "text": "A sustained dip usually means accumulated fatigue, illness or poor sleep. Consider an easier day."})

    poor = metrics.poor_sleep_nights(today)
    if poor >= 3:
        out.append({"level": "warn", "title": f"Poor sleep on {poor} of the last 7 nights",
                    "text": "Sleep score under 60. Move hard sessions to after a better night if the week allows."})

    band = metrics.acwr_band(ratio)
    if band == "high":
        out.append({"level": "bad", "title": f"Load ratio {ratio}: injury-risk zone",
                    "text": "Your last 7 days are well above your 28-day average. Back off before adding more."})
    elif band == "low":
        out.append({"level": "info", "title": f"Load ratio {ratio}: room to build",
                    "text": "You're training below your recent average. A real session is fine if you feel good."})
    elif band == "optimal":
        out.append({"level": "good", "title": f"Load ratio {ratio}: optimal zone",
                    "text": "Load is balanced against your recent history. A 5–10% step up next week is reasonable."})

    # a planned run that already happened is the same run, so count days
    runs = sum(
        1 for d in week
        if any("run" in (t or "") for t in d["done"])
        or (d["date"] >= today.isoformat() and any(p["type"] == "running" for p in d["planned"]))
    )
    if runs > 1:
        out.append({"level": "bad", "title": f"{runs} runs this week",
                    "text": "The plan allows one run per week for the knee. Swap the extra one for cycling."})

    legs = Activity.objects.filter(start_time__date__gt=today - dt.timedelta(days=10),
                                   activity_type__icontains="strength").exists()
    if not legs:
        out.append({"level": "info", "title": "No strength session in 10 days",
                    "text": "Hamstrings and glutes are your documented weak spot. Worth fitting a gym day in."})

    ftp = FTPRecord.objects.order_by("-date").first()
    if ftp and (today - ftp.date).days > 70:
        weeks = (today - ftp.date).days // 7
        out.append({"level": "info", "title": f"FTP {ftp.ftp_watts} W is {weeks} weeks old",
                    "text": "Power targets are based on it. A new test would keep your indoor workouts accurate."})

    order = {"bad": 0, "warn": 1, "info": 2, "good": 3}
    return sorted(out, key=lambda i: order[i["level"]])


@login_required
def today_page(request):
    return render(request, "coach/today.html")


@login_required
@require_http_methods(["GET"])
def today_data(request):
    today = dt.date.today()

    hrv_row = HRVRecord.objects.filter(date=today).first() or HRVRecord.objects.order_by("-date").first()
    hrv_today = hrv_row.hrv_rmssd if hrv_row else None
    baseline = metrics.hrv_baseline(today)
    sleep = SleepRecord.objects.order_by("-date").first()
    acute, chronic, ratio = metrics.acwr(today)
    score, parts = metrics.readiness(hrv_today, baseline, sleep.score if sleep else None, ratio)
    label, level = metrics.readiness_label(score)
    stats = DailyStats.objects.order_by("-date").first()

    hrv_7 = list(HRVRecord.objects.filter(date__gt=today - dt.timedelta(days=7), date__lte=today)
                 .order_by("date").values("date", "hrv_rmssd", "resting_hr"))
    week = _week(today)
    mean, sd = baseline

    return JsonResponse({
        "today": today.isoformat(),
        "last_sync": stats.date.isoformat() if stats else None,
        "readiness": {"score": score, "label": label, "level": level, "parts": parts},
        "hrv": {
            "today": round(hrv_today) if hrv_today is not None else None,
            "date": hrv_row.date.isoformat() if hrv_row else None,
            "resting_hr": hrv_row.resting_hr if hrv_row else None,
            "baseline_mean": round(mean) if mean else None,
            "baseline_sd": round(sd, 1) if sd else None,
            "last_7": [{"date": h["date"].isoformat(), "hrv": h["hrv_rmssd"], "rhr": h["resting_hr"]} for h in hrv_7],
        },
        "sleep": None if not sleep else {
            "date": sleep.date.isoformat(), "score": sleep.score, "hours": sleep.duration_hours,
            "deep": sleep.deep_sleep_hours, "rem": sleep.rem_sleep_hours, "light": sleep.light_sleep_hours,
            "awake": sleep.awake_hours, "body_battery_change": sleep.body_battery_change,
        },
        "load": {"acute_7d": round(acute), "chronic_28d": round(chronic), "ratio": ratio,
                 "band": metrics.acwr_band(ratio), "weekly": _weekly_load(today)},
        "body_battery": None if not stats else {"high": stats.body_battery_high, "low": stats.body_battery_low,
                                                "stress": stats.stress_level_avg},
        "today_sessions": [_session_dict(s) for s in
                           PlannedSession.objects.filter(date=today).exclude(activity_type="rest").prefetch_related("exercises")],
        "next_session": next((_session_dict(s) for s in
                              PlannedSession.objects.filter(date__gt=today).exclude(activity_type="rest")
                              .order_by("date").prefetch_related("exercises")[:1]), None),
        "week": week,
        "latest_activity": _latest_activity(),
        "hr_zones": (UserProfile.objects.filter(pk=1).values_list("hr_zones", flat=True).first()),
        "insights": build_insights(today, hrv_today, baseline, ratio, week),
    })
