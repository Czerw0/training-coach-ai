import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.timesince import timesince

from coach.agent import chat
from coach.models import Message
from sync.models import DailyStats

import threading
from django.core.management import call_command
from coach.models import SyncStatus


# Maps internal tool names -> friendly labels shown under the coach's reply
TOOL_LABELS = {
    "sync_all_data": "Synced data",
    "log_daily_feeling": "Logged how you feel",
    "log_injury": "Logged injury",
    "resolve_injury": "Marked injury resolved",
    "adjust_goal": "Updated goal",
    "append_athlete_note": "Saved a note",
}


def _last_update_text():
    last_row = DailyStats.objects.order_by('-updated_at').first()
    if not last_row or not last_row.updated_at:
        return None
    return f"{timesince(last_row.updated_at)} ago"


@ensure_csrf_cookie
def chat_page(request):
    past_messages = Message.objects.all().order_by('created_at')
    return render(request, 'coach/chat.html', {
        'past_messages': past_messages,
        'last_update': _last_update_text(),
    })


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


@require_http_methods(["POST"])
def chat_reset(request):
    """Delete the stored conversation (used by the 'reset' path if kept)."""
    Message.objects.all().delete()
    return JsonResponse({'status': 'reset'})


def _run_sync():
    status, _ = SyncStatus.objects.get_or_create(pk=1)
    status.state = "running"; status.message = "Syncing Garmin + weather…"; status.save()
    try:
        call_command('sync_garmin', days=1)
        call_command('sync_weather')
        status.state = "done"; status.message = "Up to date"; status.save()
    except Exception as e:
        status.state = "error"; status.message = f"Sync failed: {e}"; status.save()

@require_http_methods(["POST"])
def sync_now(request):
    status, _ = SyncStatus.objects.get_or_create(pk=1)
    if status.state == "running":
        return JsonResponse({'state': 'running', 'message': 'Already syncing…'})
    # fire-and-forget background thread
    threading.Thread(target=_run_sync, daemon=True).start()
    return JsonResponse({'state': 'running', 'message': 'Sync started…'})

@require_http_methods(["GET"])
def sync_status(request):
    status, _ = SyncStatus.objects.get_or_create(pk=1)
    return JsonResponse({'state': status.state, 'message': status.message})