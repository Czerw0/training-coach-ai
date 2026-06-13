from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from coach.agent import chat


@ensure_csrf_cookie
def chat_page(request):
    """Render the chat page."""
    # Clear history when loading a fresh page if you want each visit to start clean.
    # Comment this out to persist across page reloads.
    return render(request, 'coach/chat.html')


@require_http_methods(["POST"])
def chat_message(request):
    """Handle a single chat message via AJAX."""
    data = json.loads(request.body)
    user_message = data.get('message', '').strip()

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Pull conversation history from the session
    history = request.session.get('chat_history', [])

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