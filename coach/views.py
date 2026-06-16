import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.timesince import timesince
from django.contrib.auth.decorators import login_required

from coach.agent import chat
from coach.models import Message, PlannedSession
from sync.models import DailyStats, Activity


# Maps internal tool names -> friendly labels shown under the coach's reply
TOOL_LABELS = {
    "log_daily_feeling": "Logged how you feel",
    "log_injury": "Logged injury",
    "resolve_injury": "Marked injury resolved",
    "adjust_goal": "Updated goal",
    "append_athlete_note": "Saved a note",
    "create_planned_session": "Planned a session",
    "clear_planned_sessions": "Cleared planned sessions",
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

    # Build history for the model: last 20 messages, oldest-first
    recent = Message.objects.order_by('-created_at')[:20]
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent)
    ]

    # Call the agent ONCE
    try:
        reply, tools_used = chat(user_message, history)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Persist both sides
    Message.objects.create(role="user", content=user_message)
    Message.objects.create(role="assistant", content=reply)

    # Friendly labels for the tools that ran this turn
    actions = [TOOL_LABELS.get(t, t) for t in tools_used]

    return JsonResponse({'reply': reply, 'actions': actions})


@login_required
@require_http_methods(["POST"])
def chat_reset(request):
    """Delete the stored conversation (used by the 'reset' path if kept)."""
    Message.objects.all().delete()
    return JsonResponse({'status': 'reset'})

# --- colour map shared by activities + planned sessions ---
def _activity_color(activity_type):
    t = (activity_type or "").lower()
    if "cycl" in t or "bik" in t:                          return "#2D6CDF"   # blue
    if "strength" in t or "gym" in t or "weight" in t:     return "#7A5CCC"   # purple
    if "skat" in t:                                        return "#1D9E75"   # teal
    if "tennis" in t:                                      return "#BA7517"   # amber
    if "ski" in t:                                         return "#378ADD"   # light blue
    if "run" in t:                                         return "#E24B4A"   # red
    if "swim" in t:                                        return "#15A0A6"   # cyan
    if "hiking" in t:                                      return "#645F43D6" # brown
    return "#B1B1B1C8"                                                        # grey (rest/other)

 
# --- the calendar page ---
@login_required
def calendar_page(request):
    return render(request, 'coach/calendar.html')
 
 
# --- JSON feed FullCalendar reads ---
@login_required
@require_http_methods(["GET"])
def calendar_events(request):
    events = []

    # ---- synced activities: solid colour bar, short label ----
    for a in Activity.objects.exclude(start_time__isnull=True):
        color = _activity_color(a.activity_type)
        label = (a.activity_type or "activity").replace("_", " ").title()

        # full detail for the popup
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
            "title": label,                       # SHORT — just the type
            "start": a.start_time.date().isoformat(),   # date only -> clean all-day bar in month view
            "allDay": True,
            "backgroundColor": color,
            "borderColor": color,
            "textColor": "#fff",
            "extendedProps": {"kind": "activity", "detail": detail},
        })

    # ---- planned sessions (editable, outline style) ----
    for p in PlannedSession.objects.all():
        color = _activity_color(p.activity_type)
        label = p.title or p.activity_type.replace("_", " ").title()
        who = "User" if p.created_by == "user" else "Coach"
        status = "🟢" if p.completed else "🟡"
        events.append({
            "title": f"{status} {who} {label}",
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
            },
        })

    return JsonResponse(events, safe=False)
 
 
# --- create or update a planned session from the UI modal ---
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
    if sid:
        PlannedSession.objects.filter(id=sid).update(**fields)   # edit: keep original created_by        
    else:
        fields["created_by"] = "human"                            # new via UI
        PlannedSession.objects.create(**fields)
    return JsonResponse({"ok": True})
 
 
# --- delete a planned session from the UI modal ---
@login_required
@require_http_methods(["POST"])
def delete_planned_session(request):
    data = json.loads(request.body)
    PlannedSession.objects.filter(id=data.get("id")).delete()
    return JsonResponse({"ok": True})
 