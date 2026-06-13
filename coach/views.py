from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from coach.agent import chat
from coach.models import Message, CoachRecommendation


@ensure_csrf_cookie
def chat_page(request):
    past_messages = Message.objects.all()
    return render(request, 'coach/chat.html', {'past_messages': past_messages})


@require_http_methods(["POST"])
def chat_message(request):
    """Handle a single chat message via AJAX."""
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Pull conversation history from the session
    # Build history from all past messages
    recent = Message.objects.order_by('-created_at')[:20]  # Get last 20 messages
    history = [
        {"role": m.role, "content": m.content}
        for m in reversed(recent)
    ]

    reply = chat(user_message, history)

    # Save both sides
    Message.objects.create(role="user", content=user_message)
    Message.objects.create(role="assistant", content=reply)

    # Call the agent
    try:
        reply = chat(user_message, history)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    # Update history with this exchange
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": reply})
    request.session['chat_history'] = history
    request.session.modified = True

    return JsonResponse({'reply': reply})


@require_http_methods(["POST"])
def chat_reset(request):
    """Clear the conversation history."""
    request.session['chat_history'] = []
    request.session.modified = True
    return JsonResponse({'status': 'reset'})