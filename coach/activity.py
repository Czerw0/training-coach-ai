"""Activity detail and activity list. Read-only views over synced Garmin data."""
import datetime as dt

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from coach.dashboard import group_sets
from coach.models import PlannedSession
from sync.models import Activity, UserProfile

# (field, label, unit, decimals, sport) — sport None = shown for every activity that has it.
# A metric is shown only when the activity has a value for it.
METRICS = [
    ("minutes", "Time", "min", 0, None),
    ("km", "Distance", "km", 1, None),
    ("pace", "Pace", "/km", None, "running"),
    ("avg_hr", "Avg HR", "bpm", 0, None),
    ("max_hr", "Max HR", "bpm", 0, None),
    ("training_load", "Training load", "", 0, None),
    ("avg_power", "Avg power", "W", 0, "cycling"),
    ("normalized_power", "Normalized power", "W", 0, "cycling"),
    ("max_power", "Max power", "W", 0, "cycling"),
    ("tss", "TSS", "", 0, "cycling"),
    ("intensity_factor", "Intensity factor", "", 2, "cycling"),
    ("avg_bike_cadence", "Cadence", "rpm", 0, "cycling"),
    ("avg_running_cadence", "Cadence", "spm", 0, "running"),
    ("avg_stride_length_cm", "Stride", "cm", 0, "running"),
    ("avg_vertical_oscillation_cm", "Vertical oscillation", "cm", 1, "running"),
    ("avg_ground_contact_time_ms", "Ground contact", "ms", 0, "running"),
    ("avg_running_power", "Running power", "W", 0, "running"),
    ("total_sets", "Sets", "", 0, "strength"),
    ("total_reps", "Reps", "", 0, "strength"),
    ("avg_swolf", "SWOLF", "", 0, "swimming"),
    ("lap_count", "Laps", "", 0, "swimming"),
    ("elevation_gain_m", "Elevation gain", "m", 0, None),
    ("calories", "Calories", "kcal", 0, None),
    ("training_effect_aerobic", "Aerobic effect", "", 1, None),
    ("training_effect_anaerobic", "Anaerobic effect", "", 1, None),
    ("body_battery_delta", "Body Battery", "", 0, None),
]
# for these a lower number is the better one (shown green when it drops)
LOWER_IS_BETTER = {"pace", "avg_ground_contact_time_ms", "avg_vertical_oscillation_cm"}


def sport_of(activity_type):
    t = (activity_type or "").lower()
    if "cycl" in t or "bik" in t:
        return "cycling"
    if "run" in t or "treadmill" in t:
        return "running"
    if "strength" in t or "gym" in t:
        return "strength"
    if "swim" in t:
        return "swimming"
    return "other"


def derived(a):
    """Values for METRICS, including the computed ones (minutes, km, pace)."""
    v = {f: getattr(a, f, None) for f, *_ in METRICS if hasattr(a, f)}
    v["minutes"] = a.duration_seconds / 60 if a.duration_seconds else None
    v["km"] = a.distance_meters / 1000 if a.distance_meters else None
    v["pace"] = (a.duration_seconds / v["km"]) if v["km"] and a.duration_seconds and sport_of(a.activity_type) == "running" else None
    return v


def _avg(values):
    values = [x for x in values if x is not None]
    return sum(values) / len(values) if values else None


def metric_rows(a, comparables):
    sport = sport_of(a.activity_type)
    mine, others = derived(a), [derived(c) for c in comparables]
    rows = []
    for field, label, unit, decimals, only in METRICS:
        if only and only != sport:
            continue
        value = mine.get(field)
        if value is None or value == 0 and field not in ("body_battery_delta",):
            continue
        avg = _avg([o.get(field) for o in others]) if len(others) >= 3 else None
        delta = round((value - avg) / avg * 100) if avg else None
        rows.append({"key": field, "label": label, "unit": unit,
                     "value": value if decimals is None else round(value, decimals),
                     "avg": None if avg is None else (avg if decimals is None else round(avg, decimals)),
                     "delta_pct": delta, "lower_is_better": field in LOWER_IS_BETTER})
    return rows


def _zones(a, prefix, n):
    secs = [getattr(a, f"{prefix}_zone_{i}_seconds") or 0 for i in range(1, n + 1)]
    return [round(s / 60) for s in secs] if any(secs) else None


def activity_payload(a):
    start = a.start_time
    comparables = list(Activity.objects.filter(
        activity_type=a.activity_type, start_time__gte=start - dt.timedelta(days=90), start_time__lt=start,
    ).order_by("-start_time")[:40])
    recent = list(Activity.objects.filter(activity_type=a.activity_type, start_time__lte=start)
                  .order_by("-start_time").values("id", "start_time", "training_load", "duration_seconds")[:10])[::-1]
    plan = (PlannedSession.objects.filter(date=start.date()).exclude(activity_type="rest")
            .prefetch_related("exercises").first())
    prev = Activity.objects.filter(start_time__lt=start).order_by("-start_time").values("id", "activity_name", "activity_type").first()
    nxt = Activity.objects.filter(start_time__gt=start).order_by("start_time").values("id", "activity_name", "activity_type").first()
    profile = UserProfile.objects.filter(pk=1).first()
    return {
        "id": a.id, "name": a.activity_name or a.activity_type, "type": a.activity_type, "sport": sport_of(a.activity_type),
        "start": start.isoformat(), "location": a.location_name,
        "effect_label": a.training_effect_label, "temp": [a.min_temp, a.max_temp] if a.max_temp is not None else None,
        "metrics": metric_rows(a, comparables), "compared_with": len(comparables),
        "hr_zones": _zones(a, "hr", 5), "power_zones": _zones(a, "power", 6),
        "hr_zone_bounds": profile.hr_zones if profile else None, "ftp": profile.ftp_watts if profile else None,
        "exercises": group_sets(a.exercise_sets) if a.exercise_sets else [],
        "recent": [{"id": r["id"], "date": r["start_time"].date().isoformat(), "load": round(r["training_load"] or 0),
                    "minutes": round((r["duration_seconds"] or 0) / 60)} for r in recent],
        "plan": None if not plan else {
            "title": plan.title or plan.activity_type, "activity_type": plan.activity_type,
            "duration_minutes": plan.duration_minutes, "intensity": plan.intensity, "description": plan.description,
            "exercises": list(plan.exercises.values("name", "sets", "reps", "weight_kg"))},
        "prev": prev, "next": nxt,
    }


@login_required
def activity_page(request, activity_id):
    get_object_or_404(Activity, id=activity_id)
    return render(request, "coach/activity.html", {"activity_id": activity_id})


@login_required
@require_http_methods(["GET"])
def activity_data(request, activity_id):
    a = Activity.objects.filter(id=activity_id).first()
    if not a or not a.start_time:
        raise Http404
    return JsonResponse(activity_payload(a))


@login_required
def activities_page(request):
    return render(request, "coach/activities.html")


SPORT_FILTERS = {
    "cycling": Q(activity_type__icontains="cycl") | Q(activity_type__icontains="bik"),
    "running": Q(activity_type__icontains="run") | Q(activity_type__icontains="treadmill"),
    "strength": Q(activity_type__icontains="strength"),
    "skating": Q(activity_type__icontains="skat"),
    "other": ~(Q(activity_type__icontains="cycl") | Q(activity_type__icontains="bik") | Q(activity_type__icontains="run")
               | Q(activity_type__icontains="treadmill") | Q(activity_type__icontains="strength") | Q(activity_type__icontains="skat")),
}


@login_required
@require_http_methods(["GET"])
def activities_data(request):
    qs = Activity.objects.exclude(start_time__isnull=True).order_by("-start_time")
    sport = request.GET.get("sport")
    if sport in SPORT_FILTERS:
        qs = qs.filter(SPORT_FILTERS[sport])
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(activity_name__icontains=q) | Q(activity_type__icontains=q))
    try:
        page_no = max(1, int(request.GET.get("page", 1)))
    except ValueError:
        page_no = 1
    page = Paginator(qs.values("id", "activity_name", "activity_type", "start_time", "duration_seconds",
                               "distance_meters", "training_load", "avg_hr"), 30).get_page(page_no)
    insighted = set()
    try:
        from coach.models import AiInsight
        insighted = set(AiInsight.objects.filter(scope="activity", key__in=[str(r["id"]) for r in page])
                        .values_list("key", flat=True))
    except ImportError:
        pass
    return JsonResponse({
        "page": page.number, "pages": page.paginator.num_pages, "total": page.paginator.count,
        "items": [{"id": r["id"], "name": r["activity_name"] or r["activity_type"], "type": r["activity_type"],
                   "date": r["start_time"].date().isoformat(),
                   "minutes": round(r["duration_seconds"] / 60) if r["duration_seconds"] else None,
                   "km": round(r["distance_meters"] / 1000, 1) if r["distance_meters"] else None,
                   "load": round(r["training_load"]) if r["training_load"] else None, "avg_hr": r["avg_hr"],
                   "has_insights": str(r["id"]) in insighted} for r in page],
    })
