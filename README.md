# AI Training Coach

I built my own coach: an AI agent that reads my actual data - every ride,
every night of sleep, every HRV reading, even the weather in Warsaw — and tells
me exactly what to train today and why.

It is not a demo. It runs in production on a cloud VM, deploys itself through a
tested CI/CD pipeline, syncs data nine times a day, and I can tell you what
every single message costs me (about half a cent).

## What it does

- Pulls my Garmin data on a schedule: activities with full power/HR/TSS detail,
  sleep, HRV, daily stats — plus a local weather forecast.
- A chat interface where the coach reads everything current and gives one
  specific, justified recommendation. Not a menu. A decision.
- The agent acts, not just talks: it logs how I feel, tracks injuries, manages
  goals, saves durable facts to my profile, and writes training plans straight
  into a calendar it can also read back.
- A month-view calendar mixing what I actually did (from Garmin) with what is
  planned — each plan tagged with who made it, the AI or me.
- A trace panel next to the chat that shows the agent's actual reasoning,
  round by round: which data it pulled, what it saw, and how that led to the
  plan — surfaced from the model's extended thinking, not a paraphrase.
- A stats view: training by type, weekly volume, and plan adherence (did the
  planned sessions actually happen?).
- A live cost dashboard: tokens and dollars per message, spend over time, and
  which tools fired on every turn, filterable by model and config version.

## Architecture

```
Garmin Connect      Open-Meteo
      |                 |
      v                 v
GitHub Actions (scheduled syncs, ~9x/day)
      |
      v
PostgreSQL (Supabase)
      |
      v
Context builder ------ token-optimized snapshot:
      |                precomputed dates, summarized weather,
      |                windowed history, ACWR, planned sessions
      v
Claude Sonnet 5 agent - tool loop (extended thinking): feelings,
      |               injuries, goals, athlete notes, calendar
      |               writes, exercise/workout lookups
      v
Django web app ------ chat / calendar / stats / usage dashboard
      |
      v
Docker on Oracle Cloud VM behind Caddy (HTTPS; deployed only if tests pass)
```

Two Django apps, clean boundary: `sync` ingests data, `coach` owns the agent,
its tools, the context builder and the UI.

## Stack

Python, Django, PostgreSQL (Supabase), Anthropic API (Claude Sonnet 5),
Pydantic, garminconnect, Open-Meteo, FullCalendar, Chart.js, Docker, gunicorn,
whitenoise, Caddy, GitHub Actions, pytest.

## Engineering decisions I would defend in a review

The interesting parts of this project are the decisions — including the
features I killed.

**The agent can see its own writes.** Early on, the agent wrote calendar
sessions it could never see again, so it duplicated plans and could not answer
"what is already scheduled?". The fix was architecture, not prompting: planned
sessions became part of the context it receives. If an agent mutates state, it
must be able to read that state back. This one principle fixed half my bugs.

**I swapped Haiku for Sonnet 5 when I hit a capability ceiling, not a prompt
bug.** Haiku 4.5 kept producing wrong-day plans on multi-day date arithmetic
and would not reliably hold the anti-fabrication rules no matter how I wrote
the prompt. I precompute the dates now so the model never does calendar math
(below), but the fabrication problem was the model, not the instructions — I
confirmed it was a ceiling by trying to prompt around it and failing. A model
swap is not a one-line change either: Sonnet 5 dropped `temperature` and
`budget_tokens` entirely, so the switch meant re-checking every accepted
parameter and the pricing, not just the model string. (The `budget_tokens`
removal bit me again later — the old extended-thinking shape 400s on Sonnet 5.)

**LLM output never reaches the database unvalidated.** Calendar-writing tools
run the model's arguments through Pydantic schemas and a date-vs-weekday check
before anything is written — the code is the gatekeeper, the model is not
trusted to self-check. A model told the weekday for every date can still hand
back a mismatched pair; catching it in code turns a class of silent wrong-day
bugs into a tool error the model has to fix and retry.

**I removed the sync button.** A "sync now" feature ran a full Garmin sync
inside the web request — on a 1 GB VM that killed the worker mid-call, so I
paid for API responses that never arrived. Deleted the feature. Syncs now run
on GitHub's machines on a schedule, and the UI shows data freshness instead of
faking real-time. Removing it was the right call and I would do it again.

**I benchmarked prompt caching, killed it, then brought it back for a reason
the first attempt missed.** First try was on Haiku: I hit the model's
2,048-token caching minimum, extended the cached prefix through the tool
definitions to clear it, watched a 46k-token cache write land — and then
measured reads: zero. A five-minute TTL against my bursty, infrequent usage
meant I paid the 1.25x write premium and never collected the discount, so I
reverted it and kept the measurement rig. On Sonnet 5 it earns its place,
because a single coaching turn isn't one API call — the tool-use loop re-sends
an identical instructions+tools+data prefix milliseconds apart on each round.
That's a guaranteed same-turn cache hit, not a bet on the TTL. Same feature,
opposite verdict, because the usage pattern I measured against changed.

**Every message has a price tag.** Each chat turn writes one row: all four
token counts, computed cost, tools used, prompt version. The dashboard sits on
top. Total damage: about $5/month. After trimming the context windows to what
coaching actually needs (28 days of load for ACWR, 14 of activities, 30 of FTP
history), I stopped optimizing — because chasing pennies past that point is
bad engineering too.

**I turned the agent's reasoning on, and chose to pay for it.** Sonnet 5's
extended thinking (adaptive, low effort) drives the trace panel — I can watch
the round-by-round reasoning instead of guessing at it. Thinking bills as
output tokens, so this is a standing per-turn cost increase, not a free
feature. I estimated it against a real measured turn before flipping it on and
took the trade deliberately, because seeing *why* the coach decided something
is worth more to me than the cents. It carries its own config version so I can
compare cost with and without.

**One worker, 120-second timeout.** Free-tier VM, 1 GB RAM, 2 GB swap. Three
gunicorn workers meant OOM crash-loops; one worker is boring and stable.
Boring and stable wins.

**Everything pinned.** An unpinned dependency once auto-built a broken version
on deploy and crash-looped the app for hours. Now the SDK is pinned, the
requirements are frozen, and I verify the installed version inside the
container instead of trusting the build. That lesson cost me an evening; it
will not cost me two.

**Tests gate the deploy.** Every push runs the pytest suite on a clean runner
with a throwaway sqlite database and dummy credentials. The deploy job
literally cannot start unless tests pass. Broken code can reach the repo; it
cannot reach the server.

**Prompts are versioned like models.** The system prompt carries a version
label plus a content hash, stored with every logged turn. When I change the
coaching instructions, I compare behavior and cost across versions instead of
guessing. Treat the prompt as config, because it is.

## The agent, briefly

Standard tool-use loop — instructions plus a fresh data snapshot, tools that
hit the database, loop until a final reply. The details that actually mattered:

- Dates are precomputed. The model receives today and the next 14 days with
  weekdays already resolved, because LLM calendar math produced wrong-day plans.
- Weather is compressed into day-part blocks instead of hourly rows. Same
  decision value, fraction of the tokens.
- The prompt has hard anti-fabrication rules: never claim an action without a
  tool call this turn, persist durable facts instead of "remembering" them,
  clear a day before re-planning it.
- Quality problems were found by reading real transcripts, then fixed at the
  right layer: missing data is an architecture fix, sloppy behavior is a
  prompt fix, and some things are model limits you mitigate, not cure.

## Testing

pytest + pytest-django. Pure logic first: context helpers (unit conversion,
null handling, weather bucketing including the block boundaries) and the cost
math, which I extracted into a pure function specifically so it could be
tested. Factory helpers with realistic data. The agent tests mock the Anthropic
response, so the whole suite runs in CI before every deploy at zero API cost.

On top of that sits an eval harness (`manage.py run_evals`): a golden set of
conversations with the tool calls I expect, run against the real model so a
prompt or model change gets scored instead of eyeballed. It runs against a
throwaway test database with per-case rollback, so it never touches real data.
This is the layer that would have caught the extended-thinking API-shape bug
the mocked suite could not — mocks assert the code, not the live API contract.

## Running locally

```
git clone https://github.com/Czerw0/training-coach-ai.git
cd training-coach-ai
python -m venv venv && venv\Scripts\activate   # Windows
pip install -r requirements.txt -r requirements-dev.txt
```

`.env` in the project root:

```
SECRET_KEY=...
DEBUG=True
DATABASE_URL=postgres://...        # or sqlite:///db.sqlite3 to try it out
ANTHROPIC_API_KEY=...
GARMIN_EMAIL=...
GARMIN_PASSWORD=...
ALLOWED_HOSTS=localhost,127.0.0.1
```

Then:

```
python manage.py migrate
python manage.py createsuperuser
python manage.py sync_garmin
python manage.py sync_weather
python manage.py runserver
```

Tests: `pytest -v`.


## What is next

- Wire the training-planner skill into the live agent. `skills/training-planner`
  is a self-contained, portable Anthropic Agent Skill: per-session
  planning/scheduling methodology behind progressive disclosure, plus a
  *deterministic* week checker (`check_week.py`) that enforces spacing, same-day
  conflicts and per-axis fatigue saturation in code rather than in prose — so a
  persuasive prompt can't argue the plan out of a hard rule. It is built and
  passes its own self-tests; the remaining step is pointing the Django agent's
  loader at it (the file layout moved, which is a deliberate, flagged break).
- Email digest of the weekly plan (management command built, SMTP + schedule
  pending).
- Per-exercise strength history as a data source. The exercise library and
  on-demand detail lookups exist ("index always, detail on demand"); the missing
  piece is logged set/rep/load history so the coach can program progression, not
  just prescribe sessions.

One athlete, one dataset, one system: real data in, decisions out, every step
deployed, tested, measured — and honest about its trade-offs.