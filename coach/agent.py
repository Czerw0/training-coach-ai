import os
import json
import datetime
import anthropic
import hashlib
from dotenv import load_dotenv
from coach.context import build_context
from coach.tools import TOOL_DEFINITIONS, execute_tool
from coach.models import CoachRecommendation, ApiUsage

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


MODEL = "claude-sonnet-5"

# Safety cap: a tool-loop turn may make several API calls
MAX_TOOL_ROUNDS = 8

# CONFIG CHANGELOG — bump whenever a system-level knob changes that isn't
# already its own ApiUsage column (model is; caching/temperature/pricing
# tier aren't). Lets the usage dashboard split cost/quality by config, not
# just by model.
# v1  no temperature (deprecated on Sonnet 5), no prompt caching
# v2  prompt caching on: instructions + tool defs + per-turn data block,
#     each with an ephemeral cache_control breakpoint (backlog item 4)
CONFIG_VERSION = "v2-notemp-cache"


# Pricing — MUST match MODEL. Sonnet 5 intro pricing (until Aug 31, 2026):
#   input $2.00 | cache write $2.50 | cache read $0.20 | output $10.00
# From Sept 1, 2026 it becomes 3.00 / 3.75 / 0.30 / 15.00 — update then.
PRICE_INPUT       = 2.00 / 1_000_000
PRICE_CACHE_WRITE = 2.50 / 1_000_000
PRICE_CACHE_READ  = 0.20 / 1_000_000
PRICE_OUTPUT      = 10.00 / 1_000_000


def compute_cost(inp, cache_write, cache_read, out):
    """Cost in USD for one turn's token counts. Pure — no DB, no side effects."""
    return (inp * PRICE_INPUT + cache_write * PRICE_CACHE_WRITE
            + cache_read * PRICE_CACHE_READ + out * PRICE_OUTPUT)

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
- Before writing planned sessions for any day, if that day already has sessions
  in the context, call clear_planned_sessions for it first. Never create a
  session for a day that already has one without clearing — it causes duplicates.
- When you say the calendar is updated, you must have called
  create_planned_session this turn for each session. If the user asks you to
  update an already-planned week, confirm what changed, don't just re-claim 'done'.
- When the athlete changes durable facts (HR zones, FTP, schedule, equipment,
  resolved injuries), call append_athlete_note to save it. Conversation memory
  is lost between sessions; only saved notes persist.

=== DATES — READ, DON'T CALCULATE ===
When scheduling a session for a named weekday, you MUST copy the exact `date`
string from next_14_days for that weekday. Do NOT write any date that does not
appear verbatim in next_14_days. If the requested day is beyond next_14_days, say
so — do not calculate it. Before confirming any date, verify the weekday and
date match a single row in next_14_days.

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
- State physiological claims as hypotheses. Do not generalize a one-time event
  (a party, a missed session) into a recurring pattern unless the athlete says
  it recurs. When unsure whether something is recurring, ask.
- When the athlete reports a new injury, ask for details (location, severity,
  onset) and log it. Then adjust the plan to avoid aggravating it. If they say
  it's fully healed, log that and resume normal training. Aways ask when resolving 
  an injury is it healed permanently or is it just short-term better state.
- For indoor cycling, pick a workout from indoor_workouts, call
  get_workout_detail(name) for exact watts, then prescribe it. Never invent
  watt numbers. Never prescribe the Ramp Test as training. Always argument for the 
  chosen workout's suitability (duration, TSS, IF) based on the athlete's current 
  load, goals, and recovery status.
- Do not plan a rest day in the calendar. Every emppty day is a rest day by default. 
  Only plan a session if you have a specific workout recommendation for that day.

=== INSTRUCTION DAYS ===
- next_14_days marks USUAL instruction days. The athlete's actual schedule
  varies — what they tell you in conversation ALWAYS overrides the flag. Skating
  activities in recent_activities also reveal when instruction actually happened.
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
  room to build. Use the precomputed interpretation field. BUT check the
  athlete's historical load first — a high ratio caused by a return from time
  off is not the same as overtraining, and long rides that are normal for this
  athlete are not anomalies.
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
this athlete well.

=== TESTING ===
If "(test)" appears at the beginning of a message, treat it as a test prompt.
You may still call tools to check that you'd do the right thing — the app
intercepts them in test mode so nothing is actually written to the database,
and tool results you see may be simulated rather than real data. Answer as you
normally would.
"""

# PROMPT CHANGELOG
# v1.0.0  initial instructions
# v1.1.0  dates: copy-from-next_14_days rule, injury follow-up rule
# v1.2.0  removed workout-database rule (no workout table in context yet),
#         indoor sessions prescribed as structured intervals instead;
#         fixed next_7_days -> next_14_days in INSTRUCTION DAYS;
#         weekday now required by calendar tools
# v1.2.1  added TESTING section: "(test)"-prefixed messages skip DB writes
# v1.2.2  TESTING section now reflects that the (test) skip is enforced in
#         code (chat()), not by asking the model to self-police — the model
#         was never a reliable gate for this (see CLAUDE.md standing rules)

PROMPT_VERSION = "v1.2.2"
PROMPT_HASH = hashlib.sha256(INSTRUCTIONS.encode()).hexdigest()[:8]
PROMPT_TAG = f"{PROMPT_VERSION}@{PROMPT_HASH}"


def build_system_prompt():
    """Static instructions + fresh data block, returned separately so each
    can get its own prompt-cache breakpoint (see TOOLS_WITH_CACHE below)."""
    context = build_context()
    data_block = (
        "\n\n=== CURRENT ATHLETE DATA ===\n"
        f"{json.dumps(context, indent=2, default=str)}"
        "\n=== END DATA ==="
    )
    return INSTRUCTIONS, data_block


# Prompt caching: TOOL_DEFINITIONS is static across every turn, so mark its
# last entry as a cache breakpoint once at import time. Anthropic caches
# everything up to and including a marked block.
TOOLS_WITH_CACHE = [dict(t) for t in TOOL_DEFINITIONS]
if TOOLS_WITH_CACHE:
    TOOLS_WITH_CACHE[-1]["cache_control"] = {"type": "ephemeral"}


def _record_usage(agg, model, api_calls, tools_used, user_message, prompt_version="",
                   config_version="", tool_trace=None, final_text=""):
    """Persist one ApiUsage row for this chat turn (dashboard data)."""
    inp = agg["input_tokens"]
    cw  = agg["cache_creation_input_tokens"]
    cr  = agg["cache_read_input_tokens"]
    out = agg["output_tokens"]

    cost = compute_cost(inp, cw, cr, out)
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
            prompt_version=prompt_version,
            config_version=config_version,
            tool_trace=tool_trace or [],
            final_text=(final_text or "")[:2000],
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

    # Code-level gate, not a prompt request: a "(test)"-prefixed message must
    # never touch real athlete data, regardless of what the model decides to
    # do. The model is not trusted to self-police this (see CLAUDE.md).
    is_test = user_message.strip().lower().startswith("(test)")

    instructions_block, data_block = build_system_prompt()
    # Two cache breakpoints: instructions are static across every turn;
    # the data block is fresh per turn but identical across this turn's
    # own tool-loop round trips — both are worth caching (see backlog item 4).
    system_prompt = [
        {"type": "text", "text": instructions_block, "cache_control": {"type": "ephemeral"}},
        {"type": "text", "text": data_block, "cache_control": {"type": "ephemeral"}},
    ]
    messages = conversation_history + [{"role": "user", "content": user_message}]

    tools_used = []
    trace = []
    api_calls = 0
    agg = {"input_tokens": 0, "cache_creation_input_tokens": 0,
           "cache_read_input_tokens": 0, "output_tokens": 0}

    for _round in range(MAX_TOOL_ROUNDS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,            # Sonnet writes longer; 1500 risked
            system=system_prompt,       # truncating mid-tool-call
            tools=TOOLS_WITH_CACHE,
            messages=messages,          # NOTE: no temperature — deprecated
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
            if not is_test:
                CoachRecommendation.objects.create(
                    date=datetime.date.today(),
                    recommendation=final_text,
                    user_message=user_message,
                )
            _record_usage(agg, MODEL, api_calls, tools_used, user_message,
                          PROMPT_TAG, CONFIG_VERSION, trace, final_text)
            return final_text, tools_used

        # Model requested tools: append its turn, run each tool, return results
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tools_used.append(block.name)
                if is_test:
                    result = (f"[test mode] '{block.name}' was not executed — "
                              "no database write happened.")
                else:
                    result = execute_tool(block.name, block.input)
                trace.append({
                    "tool": block.name,
                    "input": block.input,
                    "result": str(result)[:500],
                })
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result),
                })
        messages.append({"role": "user", "content": tool_results})

    # Loop cap reached — fail loudly but gracefully, and still log the spend
    cap_message = ("I hit my internal tool-call limit for one turn — the actions so "
                   "far ran, but please re-ask to continue.")
    _record_usage(agg, MODEL, api_calls, tools_used, user_message, PROMPT_TAG,
                  CONFIG_VERSION, trace, cap_message)
    return (cap_message, tools_used)