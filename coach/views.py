import json
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.timesince import timesince
from django.contrib.auth.decorators import login_required

from pydantic import ValidationError

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
        reply, tools_used = chat(user_message, history)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    Message.objects.create(role="user", content=user_message)
    Message.objects.create(role="assistant", content=reply)

    actions = [TOOL_LABELS.get(t, t) for t in tools_used]

    return JsonResponse({'reply': reply, 'actions': actions})


@login_required
@require_http_methods(["POST"])
def chat_reset(request):
    """Delete the stored conversation (used by the 'reset' path if kept)."""
    Message.objects.all().delete()
    return JsonResponse({'status': 'reset'})

# colour map shared by activities + planned sessions
def _activity_color(activity_type):
    t = (activity_type or "").lower()
    if "cycl" in t or "bik" in t:                          return "#2D6CDF"   # blue
    if "strength" in t or "gym" in t or "weight" in t:     return "#7A5CCC"   # purple
    if "skat" in t:                                        return "#1D9E75"   # teal
    if "tennis" in t:                                      return "#BA7517"   # amber
    if "ski" in t:                                         return "#378ADD"   # light blue
    if "run" in t:                                         return "#E24B4A"   # red
    if "swim" in t:                                        return "#15A0A6"   # cyan
    if "mountaineering" in t:                              return "#645F43D6" # brown
    return "#D6D6D696"                                                        # grey (rest/other)


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
            "textColor": "#fff",
            "editable": False,   # real Garmin data, never draggable
            "extendedProps": {"kind": "activity", "detail": detail},
        })

    # planned sessions: editable, outline style
    for p in PlannedSession.objects.all().prefetch_related('exercises'):
        color = _activity_color(p.activity_type)
        label = p.title or p.activity_type.replace("_", " ").title()
        # created_by: "ai" (tool path) / "human" (UI) / legacy "coach" value —
        # anything not "human" counts as coach-planned, matches the edit
        # modal's own "planned by AI coach" / "planned by you" wording
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
        PlannedSession.objects.filter(id=sid).update(**fields)   # keep original created_by
        session = PlannedSession.objects.get(id=sid)
    else:
        fields["created_by"] = "human"
        session = PlannedSession.objects.create(**fields)

    # replace all children — simpler than diffing against existing ids
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

    # no PLANNING_WINDOW_DAYS check here on purpose — that's the LLM's
    # visible-date guard (next_14_days), not a human's. Someone dragging on
    # the real calendar grid can target any date it shows. Only real rule:
    # no moving a session into the past.
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
    """Aggregated usage/cost data for the dashboard charts."""
    qs = ApiUsage.objects.all()
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

    return JsonResponse({
        "summary": {
            "total_cost": round(all_cost, 4),
            "month_cost": round(month_cost, 4),
            "today_cost": round(today_cost, 4),
            "total_turns": turns,
            "avg_cost": round(avg_cost, 6),
        },
        "daily": daily,
        "token_totals": token_totals,
        "recent": recent,
        "by_config": by_config,
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
@require_http_methods(["GET"])
def stats_data(request):
    """Training volume + adherence — real Activity data, not cycling-power
    metrics; the athlete's actual training is mostly strength + skating."""
    today = datetime.date.today()

    total_activities = Activity.objects.count()
    first_activity = Activity.objects.order_by('start_time').first()
    summary = {
        "total_activities": total_activities,
        "first_activity_date": first_activity.start_time.date().isoformat() if first_activity else None,
        "active_goals": Goal.objects.filter(is_active=True).count(),
        "active_injuries": Injury.objects.filter(date_resolved__isnull=True).count(),
    }

    # training by type, last 90 days
    since_90 = today - datetime.timedelta(days=90)
    by_type_90d = list(
        Activity.objects.filter(start_time__date__gte=since_90)
        .values('activity_type')
        .annotate(n=Count('id'), minutes=Sum('duration_seconds'))
        .order_by('-n')
    )
    for row in by_type_90d:
        row['minutes'] = round((row['minutes'] or 0) / 60)

    # weekly volume, last 12 weeks, Monday-start buckets
    since_12w = today - datetime.timedelta(weeks=12)
    recent = Activity.objects.filter(start_time__date__gte=since_12w).values('start_time', 'duration_seconds')
    weeks = {}
    for a in recent:
        d = a['start_time'].date()
        monday = d - datetime.timedelta(days=d.weekday())
        bucket = weeks.setdefault(monday.isoformat(), {"count": 0, "minutes": 0})
        bucket["count"] += 1
        bucket["minutes"] += round((a['duration_seconds'] or 0) / 60)
    weekly_volume = [{"week_start": k, **v} for k, v in sorted(weeks.items())]

    # adherence: date-only match against any logged activity — Garmin's
    # activity types and the planner's don't line up 1:1, so no type
    # matching. rest days excluded, they're not supposed to produce an activity
    past_sessions = PlannedSession.objects.filter(date__lt=today).exclude(activity_type='rest').order_by('-date')
    activity_dates = set(
        Activity.objects.filter(start_time__date__lt=today).values_list('start_time__date', flat=True)
    )
    matched = 0
    missed = []
    for s in past_sessions:
        if s.date in activity_dates:
            matched += 1
        elif len(missed) < 10:
            missed.append({
                "date": s.date.isoformat(),
                "title": s.title or s.activity_type,
                "activity_type": s.activity_type,
            })
    total = past_sessions.count()
    adherence = {
        "matched": matched,
        "total": total,
        "rate": round(matched / total * 100) if total else None,
        "missed": missed,
    }

    return JsonResponse({
        "summary": summary,
        "by_type_90d": by_type_90d,
        "weekly_volume": weekly_volume,
        "adherence": adherence,
    })