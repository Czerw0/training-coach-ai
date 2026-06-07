import os
import json
import anthropic
from dotenv import load_dotenv
from coach.context import build_context
import datetime
from coach.models import CoachRecommendation

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

MODEL = "claude-haiku-4-5-20251001"


def build_system_prompt():
    context = build_context()
    return f""" 

    Your prompt 

    
=== CURRENT ATHLETE DATA ===
{json.dumps(context, indent=2, default=str)}
=== END DATA ===

Respond conversationally and practically, like a knowledgeable coach who knows this person well."""


def chat(user_message, conversation_history=None):
    if conversation_history is None:
        conversation_history = []

    system_prompt = build_system_prompt()

    messages = conversation_history + [
        {"role": "user", "content": user_message}
    ]

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=system_prompt,
        messages=messages,
        temperature=0.4,
        
    )

    response_text = response.content[0].text

    # Save the recommendation so the coach remembers it across days
    CoachRecommendation.objects.create(
        date=datetime.date.today(),
        recommendation=response_text,
        user_message=user_message,
    )

    return response_text