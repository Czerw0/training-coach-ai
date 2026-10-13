"""Apex insights on demand: a few short, data-grounded bullets about one
activity or one Today/Stats tile.

One `messages.create` per set — no tools, no thinking, a compact payload built
from the same helpers the pages use. The result is saved (`AiInsight`) and
served from the DB on every revisit; only an explicit refresh calls the API
again, at most once per REFRESH_MINUTES. Every call is logged to `ApiUsage`
under its own CONFIG_VERSION so the cost shows separately from chat."""
import datetime as dt
import json
import statistics

from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from pydantic import BaseModel, Field, ValidationError

from coach import metrics
from coach.activity import activity_payload
from coach.agent import MODEL, client, compute_cost
from coach.models import AiInsight, ApiUsage, DailyFeeling, Injury
from coach.stats import feel_stats, fitness_series, injury_list
from sync.models import Activity, DailyStats, HRVRecord, SleepRecord

PROMPT_VERSION = "insights-v1.0"
CONFIG_VERSION = "insights-v1"
MAX_TOKENS = 1200
REFRESH_MINUTES = 10

# scope -> (min, max) bullets
COUNTS = {"activity": (5, 8), "sleep": (3, 3), "hrv": (3, 3), "form": (3, 3), "injuries": (3, 3)}

SYSTEM = """You are Apex, the AI training coach in the ApexFit app. The athlete is a multisport amateur (cycling, running, strength, skating) based in Warsaw.

You get one JSON object with their real data for one topic and write short insights about it.
- Use only the numbers in the data. Never invent values, dates, sessions or trends that are not there. If something is missing, don't mention it unless the gap itself matters.
- Each insight: a title of 2-7 words that states the point, and one sentence (max ~30 words) that gives the evidence from the data and, when useful, what to do about it.
- Prefer comparisons the data supports (vs their own average, vs previous days or sessions, vs their zones) over generic advice.
- Order by importance. No greetings, no disclaimers, no repeating the same point twice.
- Plain English, second person ("you"). Use the units from the data."""

SCHEMA = {
    "type": "object",
    "properties": {
        "insights": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"title": {"type": "string"}, "text": {"type": "string"}},
                "required": ["title", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["insights"],
    "additionalProperties": False,
}


class Insight(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=400)


class InsightSet(BaseModel):
    insights: list[Insight] = Field(min_length=1)


# --- payloads: compact, numbers only -------------------------------------------------

def _round(v, n=1):
    return round(v, n) if isinstance(v, float) else v


def _activity(key, today):
    a = Activity.objects.filter(id=key).first() if str(key).isdigit() else None
    if not a or not a.start_time:
        raise Http404
    p = activity_payload(a)
    day = a.start_time.date()
    sleep = SleepRecord.objects.filter(date=day).values("score", "duration_hours", "deep_sleep_hours").first()
    hrv = HRVRecord.objects.filter(date=day).values("hrv_rmssd", "hrv_status", "resting_hr").first()
    feel = DailyFeeling.objects.filter(date=day).values("muscle_soreness", "energy_level", "motivation").first()
    return {
        "activity": {"name": p["name"], "type": p["type"], "date": day.isoformat(), "start_local": timezone.localtime(a.start_time).strftime("%H:%M"),
                     "garmin_effect": p["effect_label"], "location": p["location"], "temp_c": p["temp"]},
        "metrics": [{"metric": m["label"], "value": _round(m["value"]), "unit": m["unit"],
                     "your_90d_avg": _round(m["avg"]), "delta_pct": m["delta_pct"]} for m in p["metrics"]],
        "similar_sessions_compared": p["compared_with"],
        "hr_zone_minutes": p["hr_zones"], "hr_zone_bounds_bpm": p["hr_zone_bounds"],
        "power_zone_minutes": p["power_zones"], "ftp_w": p["ftp"],
        "exercises": p["exercises"],
        "last_sessions_same_type": [{"date": r["date"], "load": r["load"], "minutes": r["minutes"]} for r in p["recent"]],
        "planned_that_day": p["plan"] and {k: p["plan"][k] for k in ("title", "activity_type", "duration_minutes", "intensity", "description")},
        "that_day": {"sleep": sleep, "hrv": hrv, "how_you_felt": feel},
        "active_injuries": [{"body_part": i.body_part, "severity": i.severity, "since": i.date_started.isoformat()}
                            for i in Injury.objects.filter(date_started__lte=day).exclude(date_resolved__lt=day)],
    }


def _sleep(key, today):
    nights = list(SleepRecord.objects.filter(date__gt=today - dt.timedelta(days=14), date__lte=today).order_by("date")
                  .values("date", "score", "duration_hours", "deep_sleep_hours", "rem_sleep_hours", "awake_hours", "body_battery_change"))
    for n in nights:
        n["date"] = n["date"].isoformat()
    scores = [n["score"] for n in nights if n["score"] is not None]
    loads = {}
    for a in Activity.objects.filter(start_time__date__gt=today - dt.timedelta(days=15), start_time__date__lte=today).values("start_time", "training_load"):
        d = a["start_time"].date().isoformat()
        loads[d] = round(loads.get(d, 0) + (a["training_load"] or 0))
    return {"today": today.isoformat(), "last_14_nights": nights,
            "avg_score_14d": round(statistics.mean(scores), 1) if scores else None,
            "nights_below_60_last_7": metrics.poor_sleep_nights(today),
            "training_load_by_day": loads}


def _hrv(key, today):
    rows = list(HRVRecord.objects.filter(date__gt=today - dt.timedelta(days=28), date__lte=today).order_by("date")
                .values("date", "hrv_rmssd", "hrv_status", "resting_hr"))
    for r in rows:
        r["date"] = r["date"].isoformat()
    mean, sd = metrics.hrv_baseline(today)
    acute, chronic, ratio = metrics.acwr(today)
    return {"today": today.isoformat(), "last_28_days": rows,
            "baseline_28d": None if mean is None else {"mean_ms": round(mean, 1), "sd_ms": round(sd, 1)},
            "load": {"acute_7d": round(acute), "chronic_28d": round(chronic), "acwr": ratio}}


def _form(key, today):
    series = fitness_series(today - dt.timedelta(days=41), today)
    acute, chronic, ratio = metrics.acwr(today)
    stats = DailyStats.objects.order_by("-date").values("date", "vo2max_running", "vo2max_cycling", "acwr_ratio", "recovery_time_hours").first()
    if stats:
        stats["date"] = stats["date"].isoformat()
    return {"today": today.isoformat(),
            "note": "ctl = 42-day fitness, atl = 7-day fatigue, tsb = ctl - atl (form), all from Garmin training load",
            "fitness_every_3_days": series[::-3][::-1], "acwr": {"acute_7d": round(acute), "chronic_28d": round(chronic), "ratio": ratio},
            "garmin_latest": stats}


def _injuries(key, today):
    feel = feel_stats(today - dt.timedelta(days=27), today)
    acute, chronic, ratio = metrics.acwr(today)
    active = [{"body_part": i.body_part, "severity": i.severity, "since": i.date_started.isoformat(),
               "days": (today - i.date_started).days, "description": i.description,
               "affects_running": i.affects_running, "affects_cycling": i.affects_cycling}
              for i in Injury.objects.filter(date_resolved__isnull=True)]
    return {"today": today.isoformat(), "active": active, "last_12_months": injury_list(today),
            "soreness_last_28d": {"avg": feel["avg"], "most_sore": feel["parts"], "after_hardest_days": feel["after_hard"]},
            "load": {"acute_7d": round(acute), "chronic_28d": round(chronic), "acwr": ratio}}


PAYLOADS = {"activity": _activity, "sleep": _sleep, "hrv": _hrv, "form": _form, "injuries": _injuries}


# --- generation -----------------------------------------------------------------------

def generate(scope, payload):
    """One model call -> (validated list of {title, text}, usage dict, cost)."""
    lo, hi = COUNTS[scope]
    count = f"exactly {lo}" if lo == hi else f"{lo} to {hi}"
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        thinking={"type": "disabled"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": f"Topic: {scope}. Write {count} insights.\n\n"
                                              + json.dumps(payload, default=str, separators=(",", ":"))}],
    )
    u = response.usage
    usage = {"input": u.input_tokens, "cache_write": u.cache_creation_input_tokens or 0,
             "cache_read": u.cache_read_input_tokens or 0, "output": u.output_tokens}
    cost = compute_cost(usage["input"], usage["cache_write"], usage["cache_read"], usage["output"])
    text = next((b.text for b in response.content if b.type == "text"), "")
    items = None
    if response.stop_reason == "end_turn":
        try:
            items = [i.model_dump() for i in InsightSet.model_validate_json(text).insights][:hi]
        except ValidationError:
            items = None
    return items, usage, cost, response.stop_reason


def _log(scope, key, usage, cost, items, stop_reason):
    try:
        ApiUsage.objects.create(
            model=MODEL, input_tokens=usage["input"], cache_creation_tokens=usage["cache_write"],
            cache_read_tokens=usage["cache_read"], output_tokens=usage["output"], cost_usd=round(cost, 6),
            api_calls=1, user_message=f"[insights] {scope}:{key}", prompt_version=PROMPT_VERSION,
            config_version=CONFIG_VERSION,
            final_text=json.dumps(items)[:2000] if items else f"no valid insights (stop_reason={stop_reason})",
        )
    except Exception:
        pass  # usage logging must never break the response


def _out(row, cached):
    out = {"ok": True, "cached": cached, "items": row.items, "created_at": row.created_at.isoformat(),
           "cost_usd": round(row.cost_usd, 4), "refresh_after_minutes": REFRESH_MINUTES}
    if row.scope == "injuries":
        # names behind the ids, so the page can drop bullets about injuries hidden on this device
        out["injury_names"] = {i["id"]: i["body_part"] for i in injury_list(dt.date.today())}
    return out


@login_required
@require_http_methods(["GET", "POST"])
def insights_view(request, scope, key):
    """GET: the saved set or 404-free `{"ok": true, "items": null}`.
    POST: return the saved set, or generate one; `?refresh=1` regenerates."""
    if scope not in PAYLOADS:
        raise Http404
    today = dt.date.today()
    if scope != "activity":
        key = today.isoformat()   # tiles: one set per day
    row = AiInsight.objects.filter(scope=scope, key=str(key)).first()

    if request.method == "GET":
        return JsonResponse(_out(row, True) if row else {"ok": True, "items": None})

    refresh = request.GET.get("refresh") == "1"
    if row and not refresh:
        return JsonResponse(_out(row, True))
    if row and refresh and timezone.now() - row.created_at < dt.timedelta(minutes=REFRESH_MINUTES):
        return JsonResponse({**_out(row, True), "ok": False,
                             "error": f"Fresh insights can be requested once every {REFRESH_MINUTES} minutes."}, status=429)

    payload = PAYLOADS[scope](key, today)
    try:
        items, usage, cost, stop_reason = generate(scope, payload)
    except Exception:
        return JsonResponse({"ok": False, "error": "Apex couldn't be reached. Try again in a moment."}, status=502)
    _log(scope, key, usage, cost, items, stop_reason)
    if not items:
        return JsonResponse({"ok": False, "error": "Apex's answer didn't come back in the expected format. Try again."}, status=502)
    row, _ = AiInsight.objects.update_or_create(
        scope=scope, key=str(key),
        defaults={"items": items, "model": MODEL, "prompt_version": PROMPT_VERSION, "cost_usd": round(cost, 6)})
    return JsonResponse(_out(row, False))
