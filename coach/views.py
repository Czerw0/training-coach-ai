import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.timesince import timesince
from django.contrib.auth.decorators import login_required

from pydantic import ValidationError

from coach import agent, prompts
from coach.agent import chat
from coach.models import Goal, Injury, Message, PlannedExercise, PlannedSession
from coach.schemas import PlannedExerciseIn
from sync.models import DailyStats, Activity, Exercise
import datetime
from django.db.models import Sum, Avg, Count
from django.db.models.functions import TruncDate
from coach.models import ApiUsage

# tool name -> friendly label shown under the coach's reply
TOOL_LABELS = {
    "log_daily_feeling": "Logged how you feel",
    "log_injury": "Logged injury",
    "resolve_injury": "Marked injury resolved",
    "adjust_goal": "Updated goal",
    "append_athlete_note": "Saved a note",
    "create_planned_session": "Planned a session",
    "clear_planned_sessions": "Cleared planned sessions",
    "get_workout_detail": "Looked up workout detail",
    "get_exercise_detail": "Looked up exercise detail",
    "get_fitness_trend": "Checked fitness trend",
    "get_resolved_injury_history": "Checked injury history",
}


def _last_update_text():
    """Relative time since the most recent Garmin data landed, e.g. '2 hours ago'."""
    last_row = DailyStats.objects.order_by('-updated_at').first()
    if not last_row or not last_row.updated_at:
        return None
    return f"{timesince(last_row.updated_at)} ago"


@login_required
@ensure_csrf_cookie
def chat_page(request):
    past_messages = Message.objects.all().order_by('created_at')
    return render(request, 'coach/chat.html', {
        'past_messages': past_messages,
        'last_update': _last_update_text(),
    })


@login_required
@require_http_methods(["POST"])
def chat_message(request):
    """Handle a single chat message via AJAX."""
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # last 20 messages, oldest-first
    recent = Message.objects.order_by('-created_at')[:20]
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent)
    ]

    try:
        reply, tools_used = chat(user_message, history, user=request.user)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    Message.objects.create(role="user", content=user_message)
    Message.objects.create(role="assistant", content=reply)

    actions = [TOOL_LABELS.get(t, t) for t in tools_used]

    # trace comes from the ApiUsage row chat() just wrote
    usage_row = ApiUsage.objects.latest("created_at")
    trace = {"tool_trace": usage_row.tool_trace, "round_notes": usage_row.round_notes}

    return JsonResponse({'reply': reply, 'actions': actions, 'trace': trace})


@login_required
@require_http_methods(["POST"])
def chat_reset(request):
    """Delete the stored conversation."""
    Message.objects.all().delete()
    return JsonResponse({'status': 'reset'})

# activity type -> palette slot; colors live in app.css (--t-*) so they follow
# the theme. Must match TC.typeKey in static/coach/js/app.js.
TYPE_KEYS = [
    ("cycl", "cycling"), ("bik", "cycling"), ("run", "running"), ("treadmill", "running"),
    ("skat", "skating"), ("tennis", "tennis"), ("plyo", "plyometrics"),
    ("ski", "outdoor"), ("hik", "outdoor"), ("mountain", "outdoor"), ("walk", "outdoor"),
    ("strength", "strength"), ("gym", "strength"), ("weight", "strength"),
]


def _activity_color(activity_type):
    t = (activity_type or "").lower()
    key = next((k for needle, k in TYPE_KEYS if needle in t), "other")
    return f"var(--t-{key})"


@login_required
def calendar_page(request):
    return render(request, 'coach/calendar.html')


# JSON feed FullCalendar reads
@login_required
@require_http_methods(["GET"])
def calendar_events(request):
    events = []

    # synced activities: solid colour bar, short label
    for a in Activity.objects.exclude(start_time__isnull=True):
        color = _activity_color(a.activity_type)
        label = (a.activity_type or "activity").replace("_", " ").title()

        # detail line for the popup
        mins = round(a.duration_seconds / 60) if a.duration_seconds else None
        bits = [label]
        if mins:
            bits.append(f"{mins} min")
        if a.distance_meters:
            bits.append(f"{a.distance_meters/1000:.1f} km")
        if a.avg_hr:
            bits.append(f"avg HR {a.avg_hr}")
        if a.tss:
            bits.append(f"TSS {round(a.tss)}")
        detail = " · ".join(bits)

        events.append({
            "title": label,
            "start": a.start_time.date().isoformat(),   # date only -> clean all-day bar in month view
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color,
            "classNames": ["activity"],
            "editable": False,   # real Garmin data, never draggable
            "extendedProps": {"kind": "activity", "detail": detail, "activity_id": a.id},
        })

    # planned sessions: editable, outline style
    for p in PlannedSession.objects.all().prefetch_related('exercises'):
        color = _activity_color(p.activity_type)
        label = p.title or p.activity_type.replace("_", " ").title()
        # anything not created_by "human" counts as coach-planned
        who = "You" if p.created_by == "human" else "Coach"
        events.append({
            "title": f"{who} · {label}",
            "start": p.date.isoformat(),
            "allDay": True,
            "classNames": ["planned"],
            "backgroundColor": "transparent",
            "borderColor": color,
            "textColor": color,
            "extendedProps": {
                "kind": "planned",
                "session_id": p.id,
                "activity_type": p.activity_type,
                "title": p.title,
                "description": p.description,
                "duration_minutes": p.duration_minutes,
                "intensity": p.intensity,
                "completed": p.completed,
                "created_by": p.created_by,
                "exercises": list(p.exercises.values('name', 'sets', 'reps', 'weight_kg', 'notes')),
            },
        })

    return JsonResponse(events, safe=False)


@login_required
@require_http_methods(["POST"])
def save_planned_session(request):
    data = json.loads(request.body)
    sid = data.get("id")
    fields = {
        "date": data["date"],
        "activity_type": data.get("activity_type", "other"),
        "title": data.get("title", "") or "",
        "description": data.get("description", "") or "",
        "duration_minutes": data.get("duration_minutes") or None,
        "intensity": data.get("intensity", "") or "",
        "completed": bool(data.get("completed", False)),
    }

    # same validation as the LLM tool path — skip a bad row, don't fail the whole save
    exercises_in = []
    for row in data.get("exercises", []) or []:
        try:
            exercises_in.append(PlannedExerciseIn(**row))
        except ValidationError:
            continue

    if sid:
        before = PlannedSession.objects.filter(id=sid).prefetch_related("exercises").first()
        if before and before.created_by != "human" and before.prescribed is None:
            # first hand edit of a coach-made session: keep the coach's version
            fields["prescribed"] = {
                "title": before.title, "duration_minutes": before.duration_minutes,
                "intensity": before.intensity,
                "exercises": list(before.exercises.values("name", "sets", "reps", "weight_kg", "notes")),
            }
        PlannedSession.objects.filter(id=sid).update(**fields)   # keep original created_by
        session = PlannedSession.objects.get(id=sid)
    else:
        fields["created_by"] = "human"
        session = PlannedSession.objects.create(**fields)

    session.exercises.all().delete()
    if exercises_in:
        PlannedExercise.objects.bulk_create([
            PlannedExercise(session=session, order=i, **ex.model_dump())
            for i, ex in enumerate(exercises_in)
        ])

    return JsonResponse({"ok": True})


# move a planned session to a new date (calendar drag-and-drop)
@login_required
@require_http_methods(["POST"])
def move_planned_session(request):
    data = json.loads(request.body)
    session = get_object_or_404(PlannedSession, id=data.get("id"))
    try:
        new_date = datetime.date.fromisoformat(data.get("date", ""))
    except (ValueError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid date."}, status=400)

    # no 14-day window here — that guard is for the LLM, not for a human
    today = datetime.date.today()
    if new_date < today:
        return JsonResponse({
            "ok": False,
            "error": "Can't move a session into the past.",
        }, status=400)

    session.date = new_date
    session.save(update_fields=["date"])
    return JsonResponse({"ok": True})


# exercise catalog for the calendar modal's autocomplete
@login_required
@require_http_methods(["GET"])
def exercise_options(request):
    return JsonResponse(
        list(Exercise.objects.order_by('name').values('name', 'category')),
        safe=False,
    )


@login_required
@require_http_methods(["POST"])
def delete_planned_session(request):
    data = json.loads(request.body)
    PlannedSession.objects.filter(id=data.get("id")).delete()
    return JsonResponse({"ok": True})
 


@login_required
def usage_page(request):
    return render(request, 'coach/usage.html')
 
 
@login_required
@require_http_methods(["GET"])
def usage_data(request):
    """Aggregated usage/cost data for the dashboard charts.

    Optional GET filters: model, config_version, since (YYYY-MM-DD),
    until (YYYY-MM-DD). Every aggregate below derives from the same
    filtered `qs`, so filtering is a single change at the top, not a change
    per chart. filter_options always reflects the FULL unfiltered table so
    the dropdowns don't shrink to whatever's currently visible.
    """
    filter_options = {
        "models": list(ApiUsage.objects.order_by('model').values_list('model', flat=True).distinct()),
        "config_versions": list(
            ApiUsage.objects.order_by('config_version').values_list('config_version', flat=True).distinct()
        ),
    }

    qs = ApiUsage.objects.all()
    model_filter = request.GET.get('model')
    if model_filter:
        qs = qs.filter(model=model_filter)
    config_filter = request.GET.get('config_version')
    if config_filter:
        qs = qs.filter(config_version=config_filter)
    since = request.GET.get('since')
    if since:
        qs = qs.filter(created_at__date__gte=since)
    until = request.GET.get('until')
    if until:
        qs = qs.filter(created_at__date__lte=until)

    today = datetime.date.today()
    month_start = today.replace(day=1)

    def total_cost(queryset):
        return queryset.aggregate(s=Sum('cost_usd'))['s'] or 0.0

    all_cost   = total_cost(qs)
    month_cost = total_cost(qs.filter(created_at__date__gte=month_start))
    today_cost = total_cost(qs.filter(created_at__date=today))
    turns      = qs.count()
    avg_cost   = (all_cost / turns) if turns else 0.0

    # daily cost, last 30 days
    start_30 = today - datetime.timedelta(days=29)
    daily_rows = (qs.filter(created_at__date__gte=start_30)
                    .annotate(d=TruncDate('created_at'))
                    .values('d')
                    .annotate(cost=Sum('cost_usd'),
                              inp=Sum('input_tokens'),
                              out=Sum('output_tokens'))
                    .order_by('d'))
    daily = [{
        "date": r["d"].isoformat(),
        "cost": round(r["cost"] or 0, 4),
        "input": r["inp"] or 0,
        "output": r["out"] or 0,
    } for r in daily_rows]

    # token totals (for the doughnut)
    tot = qs.aggregate(
        inp=Sum('input_tokens'), out=Sum('output_tokens'),
        cw=Sum('cache_creation_tokens'), cr=Sum('cache_read_tokens'),
    )
    token_totals = {
        "input": tot["inp"] or 0,
        "output": tot["out"] or 0,
        "cache_write": tot["cw"] or 0,
        "cache_read": tot["cr"] or 0,
    }

    # recent turns (timeline)
    recent = [{
        "id": u.id,
        "when": u.created_at.strftime("%d %b %H:%M"),
        "cost": round(u.cost_usd, 4),
        "tools": u.tools_used,
        "message": u.user_message,
        "input": u.input_tokens,
        "output": u.output_tokens,
    } for u in qs.order_by('-created_at')[:15]]

    # per model+config comparison — the actual A/B, nothing ever deleted
    config_rows = (qs.values('model', 'config_version')
                     .annotate(turns=Count('id'),
                               total_cost=Sum('cost_usd'),
                               avg_cost=Avg('cost_usd'),
                               avg_input=Avg('input_tokens'),
                               avg_output=Avg('output_tokens'),
                               cache_reads=Sum('cache_read_tokens'))
                     .order_by('-turns'))
    by_config = [{
        "model": r["model"],
        "config_version": r["config_version"],
        "turns": r["turns"],
        "total_cost": round(r["total_cost"] or 0, 4),
        "avg_cost": round(r["avg_cost"] or 0, 6),
        "avg_input": round(r["avg_input"] or 0),
        "avg_output": round(r["avg_output"] or 0),
        "cache_reads": r["cache_reads"] or 0,
    } for r in config_rows]

    # daily cost split by config version (stacked chart)
    daily_by_config = [{
        "date": r["d"].isoformat(), "config": r["config_version"] or "baseline", "cost": round(r["cost"] or 0, 4),
    } for r in (qs.filter(created_at__date__gte=start_30).annotate(d=TruncDate('created_at'))
                  .values('d', 'config_version').annotate(cost=Sum('cost_usd')).order_by('d'))]

    # cost per message distribution
    edges = [0.01, 0.02, 0.05, 0.10, 0.20, 0.50]
    labels = ["<1¢", "1–2¢", "2–5¢", "5–10¢", "10–20¢", "20–50¢", "50¢+"]
    buckets = [0] * len(labels)
    for c in qs.values_list('cost_usd', flat=True):
        buckets[next((i for i, edge in enumerate(edges) if c < edge), len(edges))] += 1
    cost_hist = [{"label": l, "n": n} for l, n in zip(labels, buckets)]

    # tools: how often each fires, and what tool turns cost vs plain replies
    tool_counts = {}
    with_tools, without_tools = [], []
    for u in qs.values('tools_used', 'cost_usd', 'api_calls'):
        names = [t for t in (u["tools_used"] or "").split(",") if t]
        for t in names:
            tool_counts[t] = tool_counts.get(t, 0) + 1
        (with_tools if names else without_tools).append(u["cost_usd"])
    tools = [{"tool": k, "n": v} for k, v in sorted(tool_counts.items(), key=lambda kv: -kv[1])]

    cached_in = token_totals["cache_read"]
    all_in = token_totals["input"] + token_totals["cache_write"] + cached_in
    days_in_month = (month_start.replace(month=month_start.month % 12 + 1, year=month_start.year + month_start.month // 12)
                     - month_start).days

    by_prompt = [{
        "prompt_version": r["prompt_version"] or "—", "turns": r["turns"],
        "avg_cost": round(r["avg_cost"] or 0, 6), "avg_calls": round(r["avg_calls"] or 0, 1),
    } for r in qs.values('prompt_version').annotate(turns=Count('id'), avg_cost=Avg('cost_usd'), avg_calls=Avg('api_calls'))
                 .order_by('-turns')[:8]]

    return JsonResponse({
        "summary": {
            "total_cost": round(all_cost, 4),
            "month_cost": round(month_cost, 4),
            "today_cost": round(today_cost, 4),
            "total_turns": turns,
            "avg_cost": round(avg_cost, 6),
            "month_projection": round(month_cost / today.day * days_in_month, 2) if month_cost else 0,
            "cache_hit_rate": round(cached_in / all_in * 100) if all_in else None,
            "avg_api_calls": round(qs.aggregate(a=Avg('api_calls'))['a'] or 0, 1),
            "avg_cost_with_tools": round(sum(with_tools) / len(with_tools), 4) if with_tools else None,
            "avg_cost_without_tools": round(sum(without_tools) / len(without_tools), 4) if without_tools else None,
        },
        "daily_by_config": daily_by_config,
        "cost_hist": cost_hist,
        "tools": tools,
        "by_prompt": by_prompt,
        "daily": daily,
        "token_totals": token_totals,
        "recent": recent,
        "by_config": by_config,
        "filter_options": filter_options,
    })


@login_required
def usage_detail_page(request, usage_id):
    get_object_or_404(ApiUsage, id=usage_id)
    return render(request, 'coach/usage_detail.html', {"usage_id": usage_id})


@login_required
@require_http_methods(["GET"])
def usage_detail_data(request, usage_id):
    """One turn's full trace: message -> tool calls (args + result) -> final reply."""
    u = get_object_or_404(ApiUsage, id=usage_id)
    return JsonResponse({
        "id": u.id,
        "when": u.created_at.strftime("%d %b %Y %H:%M"),
        "model": u.model,
        "config_version": u.config_version,
        "prompt_version": u.prompt_version,
        "cost": round(u.cost_usd, 6),
        "api_calls": u.api_calls,
        "input": u.input_tokens,
        "output": u.output_tokens,
        "cache_write": u.cache_creation_tokens,
        "cache_read": u.cache_read_tokens,
        "user_message": u.user_message,
        "tool_trace": u.tool_trace,
        "final_text": u.final_text,
    })


@login_required
def stats_page(request):
    return render(request, 'coach/stats.html')


@login_required
def me_page(request):
    from sync.models import UserProfile
    month_start = datetime.date.today().replace(day=1)
    return render(request, 'coach/me.html', {
        "ftp": UserProfile.objects.filter(pk=1).values_list("ftp_watts", flat=True).first(),
        "month_cost": ApiUsage.objects.filter(created_at__date__gte=month_start).aggregate(s=Sum('cost_usd'))['s'] or 0,
        "prompt_custom": prompts.active_prompt(request.user)[1] != agent.PROMPT_TAG,
    })
