# ApexFit — AI Training Coach

I built my own coach, **Apex**: an AI agent that reads my actual data - every ride,
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
- Week planning is backed by a training-planner skill: per-session methodology
  loaded on demand, plus a *deterministic* week checker that enforces spacing,
  same-day conflicts and fatigue saturation in code, not in prose.
- A month-view calendar mixing what I actually did (from Garmin) with what is
  planned — each plan tagged with who made it, the AI or me.
- A trace panel next to the chat that shows the agent's actual reasoning,
  round by round: which data it pulled, what it saw, and how that led to the
  plan — surfaced from the model's extended thinking, not a paraphrase.
- A stats view: training by type, weekly volume, plan adherence (did the
  planned sessions actually happen?), how I feel (soreness, energy, motivation)
  and an injury timeline.
- A page for every activity: sport-specific metrics compared with my own
  90-day average, HR and power zones, exercises, plan vs done, prev/next.
- Apex insights on demand: "Get insights" on an activity (5–8 bullets) or
  "Ask Apex" on the HRV, Sleep, Injuries and Form tiles (3 bullets). One cheap
  model call (no tools, no thinking, JSON-schema output validated before
  saving), stored and served from the DB on every revisit; Refresh at most
  every 10 minutes. About 1–1.5 cents a set, logged separately as `insights-v1`.
- Injuries can be hidden from view on one device (for showing the app to
  someone) — the agent and insights still see all of them.
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
      |               writes, exercise/workout lookups, training skills
      v
Django web app ------ chat / calendar / stats / usage dashboard
      |
      v
Docker on Oracle Cloud VM (deployed only if tests pass)
```

Two Django apps, clean boundary: `sync` ingests data, `coach` owns the agent,
its tools, the context builder and the UI.

```
coach/                  agent, tools, context builder, views, evals
  agent.py              system prompt, model, pricing, the tool loop
  tools.py              tool functions + their JSON schemas
  context.py            the data snapshot sent with every message
sync/                   Garmin / weather sync + seed data (management commands)
skills/training-planner portable Agent Skill: session methodology + week checker
core/                   Django settings
```

## Stack

Python, Django, PostgreSQL (Supabase), Anthropic API (Claude Sonnet 5),
Pydantic, garminconnect, Open-Meteo, FullCalendar, Chart.js, Docker, gunicorn,
whitenoise, uv, GitHub Actions, pytest.

## The agent, briefly

Standard tool-use loop — instructions plus a fresh data snapshot, tools that
hit the database, loop until a final reply. The details that actually mattered:

- Dates are precomputed. The model receives today and the next 14 days with
  weekdays already resolved, because LLM calendar math produced wrong-day plans.
  Calendar writes are validated in code against the claimed weekday.
- Model output never reaches the database unvalidated: tool inputs that write
  go through Pydantic schemas first.
- Weather is compressed into day-part blocks instead of hourly rows. Same
  decision value, fraction of the tokens.
- "Index always, detail on demand": the context carries short indexes (workouts,
  exercises, training skills); full detail is fetched by a tool only when needed.
- The prompt has hard anti-fabrication rules: never claim an action without a
  tool call this turn, persist durable facts instead of "remembering" them,
  clear a day before re-planning it.
- Quality problems were found by reading real transcripts, then fixed at the
  right layer: missing data is an architecture fix, sloppy behavior is a
  prompt fix, and some things are model limits you mitigate, not cure.

---

## Setup

### What you need

- Python 3.12
- A Garmin Connect account (the data source)
- An Anthropic API key
- A Postgres database — Supabase free tier works. For a quick local try,
  SQLite is enough.

### 1. Install

```powershell
git clone https://github.com/Czerw0/training-coach-ai.git
cd training-coach-ai
python -m venv venv
venv\Scripts\activate              # Windows; on macOS/Linux: source venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Configure `.env`

Copy the template and fill it in:

```powershell
copy .env.example .env
```

| Variable | Required | What it is |
|---|---|---|
| `SECRET_KEY` | yes | Any long random string (Django signing key) |
| `DEBUG` | no | `True` locally, `False` in production |
| `ALLOWED_HOSTS` | yes | Comma-separated hosts, e.g. `localhost,127.0.0.1` or the VM's IP |
| `CSRF_TRUSTED_ORIGINS` | prod | Full origins incl. scheme, e.g. `http://1.2.3.4:8000` |
| `DATABASE_URL` | yes | Supabase pooled connection string, or `sqlite:///db.sqlite3` |
| `ANTHROPIC_API_KEY` | yes | For the agent |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | yes | Garmin Connect login for `sync_garmin` |
| `DIRECT_DATABASE_URL` | evals only | Supabase *direct* (non-pooled, port 5432) URL for `run_evals` |
| `EMAIL`, `EMAIL_PASSWORD` | no | Gmail address + App Password for the weekly digest |
| `BEHIND_HTTPS_PROXY`, `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | no | Leave `False` until the app sits behind an HTTPS proxy |

### 3. Create the database and your login

```powershell
python manage.py migrate
python manage.py createsuperuser     # this is the account you log in with
```

### 4. Load the libraries and your data

```powershell
python manage.py sync_exercises          # gym exercise library
python manage.py sync_indoor_workouts    # indoor cycling workout catalog
python manage.py sync_garmin --days 28   # first sync: a month of history for ACWR
python manage.py sync_weather
```

Both library commands are idempotent — rerun them after editing their lists.

### 5. Fill in your athlete profile

```powershell
python manage.py runserver
```

Open http://127.0.0.1:8000/settings/ and fill in max HR, threshold HR, weight,
your heart-rate zones and — most important — injury history and notes: free text
the coach reads on every message. FTP is synced from Garmin automatically.
Warsaw and Innsbruck are preset as weather locations; add others by searching.

### 6. Use it

Open http://127.0.0.1:8000/ and log in with the superuser account.

| Page | URL | What for |
|---|---|---|
| Today | `/` | Readiness, today's session, the week, recovery, load, weather, insights |
| Apex | `/coach/` | Talk to the coach; the trace panel shows its reasoning and tool calls |
| Calendar | `/calendar/` | Done (Garmin) vs planned sessions; drag to move, click to edit |
| Stats | `/stats/` | Fitness & form, volume by sport, intensity, recovery, how you feel, injuries, FTP/VO2max, records |
| Activities | `/activities/` | Every synced session, filter by sport, search; each opens `/activity/<id>/` with insights |
| Profile | `/me/` | Links to Settings and Usage, theme, log out (the fifth tab on mobile) |
| Usage | `/usage/` | Spend and projection, cost per message, cache, tools, per model/config |
| Settings | `/settings/` | Location, athlete profile, HR zones, instruction days |
| Admin | `/admin/` | Profile, injuries, goals, raw synced data |

Things worth knowing when chatting:

- Tell it how you feel, about pain, goals or life changes — it saves those with
  tools (feelings, injuries, goals, athlete notes), so they persist between
  conversations. Chat history alone is not memory.
- "Plan my week" makes it load the training principles, draft the week, run the
  week checker and only then write sessions into the calendar.
- Start a message with `(test)` to try a prompt without writing anything: tool
  calls are intercepted in code and nothing is saved.

---

## Deployment

Production is a Docker container on a VM, with scheduled syncs on GitHub Actions.

### VM (one-time)

1. A Linux VM with Docker installed and port `8000` open in its firewall /
   cloud security list.
2. Clone the repo into the home directory and create `.env` there (production
   values: `DEBUG=False`, the VM IP in `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS`).
3. Build and start once by hand:
   ```bash
   cd training-coach-ai
   docker build -t coach .
   docker run -d --name coach --restart unless-stopped --env-file .env -p 8000:8000 coach
   ```
   The container runs migrations on start, then gunicorn.

### GitHub Actions secrets

Repo → Settings → Secrets and variables → Actions:

| Secret | Used by |
|---|---|
| `VM_HOST`, `VM_USER`, `VM_SSH_KEY` | deploy (SSH into the VM; use a dedicated key without passphrase) |
| `SECRET_KEY`, `DATABASE_URL` | Garmin + weather syncs |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | Garmin sync |

### Workflows

| Workflow | When | What |
|---|---|---|
| `deploy.yml` | push to `main`, or manual | runs the tests on SQLite; only if they pass, SSHes to the VM, pulls, rebuilds and restarts the container |
| `garmin_sync.yml` | 9x/day (UTC cron) | `sync_garmin` against the production database |
| `weather_sync.yml` | 3x/day | `sync_weather` |

Every workflow can also be started by hand: Actions → workflow → **Run workflow**.

---

## Customizing

| To change | Where |
|---|---|
| Coaching rules, safety rules, tone | `INSTRUCTIONS` in `coach/agent.py` — bump `PROMPT_VERSION` and add a changelog line |
| Model | `MODEL` in `coach/agent.py` — update the `PRICE_*` constants too, bump `CONFIG_VERSION` |
| Thinking effort, max tool rounds | `THINKING_EFFORT`, `MAX_TOOL_ROUNDS` in `coach/agent.py` |
| Personal facts (profile, injuries, HR zones) | **Settings** page, or just tell the coach |
| Skating instruction days | **Settings** page |
| Weather location (where you are now) | **Settings** page: search a city, then select it |
| Sync frequency | cron lines in `.github/workflows/garmin_sync.yml` / `weather_sync.yml` |
| Gym exercises | `EXERCISES` in `sync/management/commands/sync_exercises.py`, then rerun the command |
| Indoor cycling workouts | `WORKOUTS` in `sync/management/commands/sync_indoor_workouts.py`, then rerun |
| Training methodology | `skills/training-planner/reference/sessions/<category>/<name>.md` — a new file is picked up automatically (see below) |
| A new agent tool | `coach/tools.py`, in **three** places: the function, `TOOL_DEFINITIONS`, `TOOL_FUNCTIONS` |

### Adding a training skill

Each session type is one Markdown file with frontmatter (`name`, `category`,
`description`, load per fatigue axis, spacing, conflicts) — copy an existing
leaf as a template. The agent's index, the loader and the week checker all read
the directory, so there is nothing to register. After editing:

```powershell
python skills/training-planner/scripts/selftest.py             # validate all leaves
python skills/training-planner/scripts/catalog.py --markdown   # regenerate reference/catalog.md
```

---

## Development

### Tests

pytest + pytest-django. Pure logic first: context helpers (null handling,
weather bucketing including the block boundaries), the cost math, tool
validation and the training-skill loader. The agent tests mock the Anthropic
response, so the whole suite runs in CI before every deploy at zero API cost.

Run them against SQLite, like CI — `.env` usually points at the production
database:

```powershell
$env:DATABASE_URL="sqlite:///test.sqlite3"; pytest
```

### Evals

`manage.py run_evals` runs a golden set of conversations (`coach/evals/cases.json`)
with the tool calls I expect against the **real** model, so a prompt or model
change gets scored instead of eyeballed. It uses a throwaway test database with
per-case rollback and never touches real data. It costs real API money, so it is
a manual tool, not part of CI. Needs `DIRECT_DATABASE_URL`.

```powershell
python manage.py run_evals               # whole set
python manage.py run_evals --case <id>   # one case
```

This is the layer that would have caught the extended-thinking API-shape bug
the mocked suite could not — mocks assert the code, not the live API contract.

### Dependencies

`requirements.in` lists direct dependencies; `requirements.txt` is the pinned
lock generated from it. To add or upgrade a package:

```powershell
pip install uv                     # once
# edit requirements.in, then:
uv pip compile requirements.in -o requirements.txt --python-version 3.12 --python-platform linux
pip install -r requirements-dev.txt
```

Commit both files. Test-only tools go in `requirements-dev.txt`.

### Other commands

| Command | What |
|---|---|
| `python manage.py notifications` | email the list of planned sessions to yourself (needs `EMAIL`/`EMAIL_PASSWORD`) |
| `python manage.py sync_garmin --days N` | re-sync the last N days (default 4) |

---

## What is next

- Per-exercise strength history as a data source. The exercise library and
  on-demand detail lookups exist; the missing piece is logged set/rep/load
  history so the coach can program progression, not just prescribe sessions.
- HTTPS behind a reverse proxy (Caddy) before the app is exposed beyond me.
- Turn triage (model tier + instruction subset per message) is built but off,
  waiting for the eval harness to prove it changes nothing that matters.

One athlete, one dataset, one system: real data in, decisions out, every step
deployed, tested, measured — and honest about its trade-offs.
