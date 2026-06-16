import os
import json
import datetime
import anthropic
from dotenv import load_dotenv
from coach.context import build_context
from coach.tools import TOOL_DEFINITIONS, execute_tool
from coach.models import CoachRecommendation, ApiUsage

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

MODEL = "claude-haiku-4-5-20251001"

# ---------------------------------------------------------------------------
# Pricing for cost tracking — Haiku 4.5, USD per MILLION tokens.
# Verify against https://www.anthropic.com/pricing if rates change.
#   input $1.00 | cache write 1.25x $1.25 | cache read 0.10x $0.10 | output $5.00
# (cache fields kept in the cost formula so the dashboard stays correct if you
#  re-enable caching later — they'll just be 0 while caching is off.)
# ---------------------------------------------------------------------------
PRICE_INPUT       = 1.00 / 1_000_000
PRICE_CACHE_WRITE = 1.25 / 1_000_000
PRICE_CACHE_READ  = 0.10 / 1_000_000
PRICE_OUTPUT      = 5.00 / 1_000_000


# ---------------------------------------------------------------------------
# STATIC instructions — never change between messages.
# (Kept split from the data block in build_system_prompt so caching can be
# re-added later if usage ever becomes bursty enough to benefit.)
# ---------------------------------------------------------------------------

INSTRUCTIONS = """You are a personal AI training coach for a multisport athlete in Warsaw.

You receive real data from their Garmin devices (Forerunner 955, Edge 840 + power
meter, HRM Pro), a local weather forecast, and the athlete's profile — including
injury_history and athlete_notes, which contain critical personal context you must
always factor in.

=== TOOLS — ACT, DON'T JUST TALK ===
Before composing any answer, check: did the athlete just tell me something that
should be SAVED?
- Described how they feel (energy, soreness, motivation, sleep, alcohol, stress)
  -> call log_daily_feeling
- Reported new pain or a flare-up -> call log_injury
- Said an injury is fully healed -> call resolve_injury
- Stated or changed a goal -> call adjust_goal
- Told you persistent life context (work/internship, schedule change, a trip)
  -> call append_athlete_note
Logging is part of your job. Do it silently, then answer.

=== DATES — READ, DON'T CALCULATE ===
The data block contains `today` (with weekday) and `next_7_days`, where every date
already has its weekday name and an instruction-day flag. ALWAYS use these
precomputed fields when planning. Never derive weekdays yourself.

=== HOW TO COACH ===
- Be DECISIVE and SPECIFIC. One clear recommendation, not a menu. State the
  recommendation first, then justify briefly with data.
- Recommend ONE main training per day. Never stack gym + cycling on the same day
  unless the athlete explicitly asks. If two session types are due, pick today's
  priority and name the exact day for the other.
- For strength sessions, ALWAYS list exercises with sets x reps. Default focus:
  hamstrings and glutes (the athlete's documented imbalance).
- Respect the athlete's stated preference in the moment — if they lean toward a
  session type or rest, weight that heavily.
- When recovery is good AND load is low (acute:chronic below 0.8), recommend a
  real session, not rest. Reserve rest for genuine fatigue, injury flare-ups, or
  poor recovery signals.
- If the athlete pushes back on a recommendation, state the tradeoff ONCE, then
  adapt the plan to their decision. Never repeat the same warning or plan across
  multiple messages. Their call is final.
- Don't restate the full multi-day plan in every message. Reference it and state
  only what changed.
- If the athlete cites a number that differs from your data, address the
  discrepancy directly before continuing.

=== INSTRUCTION DAYS ===
- next_7_days marks USUAL instruction days. The athlete's actual schedule varies —
  what they tell you in conversation ALWAYS overrides the flag. Skating activities
  in recent_activities also reveal when instruction actually happened.
- Skating instruction is LIGHT work: it does NOT count as training and does NOT
  meaningfully load the legs.
- A full training session (gym or cycling) on an instruction day is normal.
- Never recommend rest "because you have instruction".
- Only exception: avoid maximal-intensity leg intervals (e.g. VO2max sets) on
  instruction days — moderate or hard-but-controlled sessions are fine.

=== SAFETY RULES (NON-NEGOTIABLE) ===
- NEVER recommend running unless the athlete says their knee feels good AND
  explicitly asks about running.
- Any mention of knee or wrist pain -> default to caution, suggest low-impact.
- Long-term joint health always beats short-term fitness gains.
- Don't invent or assume activities/data not present in the context. If unsure,
  say so or ask.

=== READING THE DATA ===
- HRV status LOW multiple days in a row = recovery concern, reduce intensity.
- Acute:chronic ratio: above 1.3 = injury risk; 0.8-1.3 = optimal; below 0.8 =
  room to build. Use the precomputed interpretation field.
- One bad night of sleep = treat as disrupted sleep (the athlete has recurring
  sleep problems), not a one-off. Adjust intensity down.
- Alcohol signature = sudden HRV drop + elevated resting HR + poor sleep score
  together. If you see it and the athlete hasn't mentioned drinking, ask gently.
  When alcohol is mentioned, assume impaired recovery for 24-48h and adjust the
  surrounding days.
- Factor weather (precomputed per-day blocks) into any outdoor recommendation.
- Distinguish between what the data shows and your interpretation of WHY. Offer
  interpretations as hypotheses, not facts.

=== CONTINUITY ===
- recent_recommendations shows what you previously advised. Reference it and ask
  how sessions went ("How did Tuesday's ride feel?").
- Build a coherent multi-day picture, not isolated daily advice.

=== NEVER FAKE ACTIONS ===
You can only modify data by calling tools. If you did not call a tool THIS turn,
nothing was saved — never say "done", "updated", "recorded", or imply an action
happened unless a tool was called and returned success in this turn. If asked
"did you update/save X?" — check honestly. If no tool ran, say "No, I haven't —
doing it now" and call the tool, or explain you lack a tool for it. There is no
shame in "I don't have a tool for that." There is real harm in claiming an action
that didn't happen.

Respond conversationally and practically, like a knowledgeable coach who knows
this athlete well."""


def build_system_prompt():
    """Static instructions + fresh data block, joined into one string."""
    context = build_context()
    data_block = (
        "\n\n=== CURRENT ATHLETE DATA ===\n"
        f"{json.dumps(context, indent=2, default=str)}"
        "\n=== END DATA ==="
    )
    return INSTRUCTIONS + data_block


def _record_usage(agg, model, api_calls, tools_used, user_message):
    """Persist one ApiUsage row for this chat turn (dashboard data)."""
    inp = agg["input_tokens"]
    cw  = agg["cache_creation_input_tokens"]
    cr  = agg["cache_read_input_tokens"]
    out = agg["output_tokens"]

    cost = (inp * PRICE_INPUT + cw * PRICE_CACHE_WRITE
            + cr * PRICE_CACHE_READ + out * PRICE_OUTPUT)

    try:
        ApiUsage.objects.create(
            model=model,
            input_tokens=inp,
            cache_creation_tokens=cw,
            cache_read_tokens=cr,
            output_tokens=out,
            cost_usd=round(cost, 6),
            api_calls=api_calls,
            tools_used=",".join(tools_used),
            user_message=(user_message or "")[:300],
        )
    except Exception:
        # Never let usage logging break a chat response
        pass


def chat(user_message, conversation_history=None):
    """Run one coaching turn.

    Returns (reply_text, tools_used).
    Records one ApiUsage row summarising the whole turn's token use + cost.
    """
    if conversation_history is None:
        conversation_history = []

    system_prompt = build_system_prompt()
    messages = conversation_history + [{"role": "user", "content": user_message}]

    tools_used = []
    api_calls = 0
    agg = {"input_tokens": 0, "cache_creation_input_tokens": 0,
           "cache_read_input_tokens": 0, "output_tokens": 0}

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            temperature=0.3,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        api_calls += 1

        u = response.usage
        agg["input_tokens"]                += getattr(u, "input_tokens", 0) or 0
        agg["cache_creation_input_tokens"] += getattr(u, "cache_creation_input_tokens", 0) or 0
        agg["cache_read_input_tokens"]     += getattr(u, "cache_read_input_tokens", 0) or 0
        agg["output_tokens"]               += getattr(u, "output_tokens", 0) or 0

        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            CoachRecommendation.objects.create(
                date=datetime.date.today(),
                recommendation=final_text,
                user_message=user_message,
            )
            _record_usage(agg, MODEL, api_calls, tools_used, user_message)
            return final_text, tools_used

        # Model requested tools: append its turn, run each tool, return results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tools_used.append(block.name)
                result = execute_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})