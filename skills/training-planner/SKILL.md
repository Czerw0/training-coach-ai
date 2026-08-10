---
name: training-planner
description: Plan and schedule endurance and strength training weeks — Z2/interval cycling and running, heavy/eccentric/power gym work, and plyometrics. Use when building or revising a training week or microcycle, placing a specific session type, checking whether two sessions can sit near each other, deciding what to downgrade on low readiness, or handling deloads, tapers and return-to-load. Carries per-session load/recovery/conflict metadata and a deterministic week checker.
---

# Training planner

On-demand methodology for planning and scheduling each kind of training session,
plus the cross-cutting load-management principles they share. Built as one
portable skill folder: it runs identically on Claude.ai, the API and Claude Code
because nothing here needs a bespoke tool — Claude reads the reference files and
runs the stdlib-only scripts.

> Everything here is a **draft for a coach to verify**. It is general
> strength-and-conditioning guidance, not individualised medical advice, and
> must be checked against the athlete's real history, injuries and goals before
> it drives a plan.

## Who this is tuned for

This library is personalised for **one athlete**; the standing context lives in
**`reference/principles/planning-the-week` §0** — load it first, don't duplicate
it here. The essentials that change how you plan:

- **Skiing is the winter goal and the north star.** It isn't trained in this
  system (it happens on-snow, in season); every summer session is justified by
  its transfer to skiing and to **long-term durability over short-term numbers**.
- **Current priorities: cycling, gym, plyometrics.** Cycling (with a direct-drive
  trainer) is the default aerobic engine.
- **Do not propose running unless the athlete explicitly asks.** Knee injury —
  default to `cycling/*` for aerobic work. When running is requested, prioritise
  `running/intervals` and `running/tempo-threshold`; `running/easy-long` is kept
  for the future but deprioritised now.
- **Plan around injuries and schedule first; keep the week flexible.** Rotate
  lower-body gym types for variety, ease leg work in cycling-heavy weeks, and
  aim for 1–3 rest days. Season phase (§0 table) sets what a good week looks like.

## How this skill is organised (progressive disclosure)

Three levels, loaded only as far down as the task needs:

1. **This file + the catalog** — the always-cheap layer. The frontmatter
   `description` above is the trigger. Once triggered, read the compact
   `reference/catalog.md` (or run `scripts/catalog.py`): one line per session
   with its load axes, recovery cost and same-day conflicts. That metadata is
   enough to **shortlist and conflict-check a whole week without opening a
   single session body**.
2. **Principles** — `reference/principles/`. Read both files **once per planning
   turn**, before any leaf: they hold the shared reasoning (fatigue axes,
   interference, progression, readiness, taper) that the leaves defer to.
3. **Session leaves** — `reference/sessions/<category>/<skill>.md`. Read only the
   2–3 you are actually going to prescribe from.

## Workflow for planning a week

```
1. Read reference/catalog.md            (the always-in-context index)
2. Read both reference/principles/*.md   (once — the shared "why")
3. Draft a week: fix immovables → key sessions → fresh-required → high-damage →
   fill with low-interference work   (planning-the-week §2)
4. Validate it deterministically:
      python scripts/check_week.py my_week.json --format text
   Fix every `error`. For every `warning`, either fix it or STATE the
   compromise in the plan (planning-the-week §3).
5. Read only the leaf files for the sessions you'll prescribe, then write each
   session, honouring its Hard rules and noting any preference you traded away.
```

Single-session requests skip steps 3–4: read the catalog line, read that one
leaf, prescribe.

## Execution over reading — the scripts

Constraint checking runs in Python, not in the model's head, so a persuasive
prompt can't argue the plan out of a hard rule. All scripts are stdlib-only.

| Script | What it does |
|---|---|
| `scripts/catalog.py` | Print the compact index; `--markdown` regenerates `reference/catalog.md` |
| `scripts/sessions.py` | `list`, or `show <category/skill>` to print one leaf body on demand |
| `scripts/check_week.py` | Validate a candidate week — same-day conflicts, spacing, per-axis saturation, day-after protection |
| `scripts/frontmatter.py` | Shared zero-dependency frontmatter parser (imported by the others) |

**check_week.py input** — a JSON array of planned sessions (see
`assets/week.example.json`):

```json
[
  {"id": "gym/lower-max-strength", "start": "2026-08-10T17:00"},
  {"id": "cycling/endurance",      "start": "2026-08-15T10:00"}
]
```

It prints violations as JSON (or `--format text`) and exits non-zero if any are
`error`-severity, so it doubles as a gate. Severity is the whole point:
`error` = the plan is wrong, fix it; `warning` = a defensible compromise you
must state rather than bury. Design decisions (spacing direction, which number
wins on disagreement, the per-axis saturation windows) are documented at the top
of the file.

## How this connects to the app's tools

This skill is the *methodology*; the surrounding agent supplies the data and
does the writing. Wire them together, and never duplicate what a tool already
provides:

- **Dates come from `next_14_days` in the context — never compute a date.** Each
  entry carries the date, weekday and instruction-day flag precisely so calendar
  arithmetic never happens in the model. Read the target day from there.
- **Weather:** place outdoor rides using `weather_next_48h`; move indoors when
  it's poor (`cycling/endurance`, `cycling/intervals`). Indoor rides can pull a
  concrete workout from the indoor-cycling catalog via `get_workout_detail`.
- **Injuries / substitutions:** when a leaf says "substitute a pain-free
  variation" (e.g. `gym/upper-body`, `gym/lower-*`), use `get_exercise_detail`
  to pick the swap rather than inventing one.
- **Writing the plan goes through the calendar tools** — `create_planned_session`
  and `clear_planned_sessions` — and **every write is validated by
  `validate_session_date`** (the model's date must match its stated weekday).
  Code is the gatekeeper; a session this skill designs is only real once a tool
  has written it and the checker/validator has passed. Run `scripts/check_week.py`
  on the draft *before* writing anything.
- **ACWR**, if present in context, is a descriptive flag only — never a gate or a
  line in the session rationale (`principles/load-and-recovery` §3).

## The file contract

Every leaf has the same frontmatter and the same eight sections. Consistency is
what lets you read only the section you need and get comparable output across
session types.

```yaml
---
name: <slug>                  # matches filename
category: <folder>
description: <one line — the "use when" that lives in the catalog>
load: {neural: ..., mechanical: ..., metabolic: ..., damage: ...}   # none|low|moderate|high
residual_fatigue_h: <int>     # hours before a key session can safely follow
same_day_conflicts: [<category/skill>, ...]
spacing_h: {<category/skill>: <hours>, ...}
pairs_well_with: [<category/skill>, ...]
prerequisites: [...]
contraindicated_if: [...]
see_also: [...]               # principles/<file> or <category/skill>
---
```

Sections, in order: **Use when · Don't use when · Prescription · Dosing and
progression · Scheduling (Hard rules vs Preferences, labelled) · Interactions ·
Stop rules · Worked example · Evidence notes (Supported vs Convention).**

Three carry most of the weight:

- **Hard rules vs preferences.** Without the split, you can't tell what may be
  traded away when the week is constrained — so you either violate a real
  constraint or refuse a workable plan.
- **Worked example.** A few-shot demonstration inside the file: the single
  cheapest lever on output quality.
- **Evidence notes.** Stops coaching convention being stated to the athlete as
  established fact.

## Adding or changing a session

Drop a new `reference/sessions/<category>/<skill>.md` with full frontmatter into
the folder. The directory scan is the single source of truth — `catalog.py`,
`sessions.py` and `check_week.py` all discover it immediately, with nothing else
to register. Then run `python scripts/catalog.py --markdown` to refresh the
catalog. Directories starting with `_` are skipped.

**Before adding one, check it is a distinct scheduling object.** A new leaf earns
its place only if it has a different `load` profile or different conflicts from
everything in the catalog. If it differs only in exercise selection, it is a
variant row in an existing file's Prescription table.

## Coverage

Full leaves currently in the library:

- **cycling:** `endurance`, `intervals`
- **gym:** `lower-max-strength`, `lower-eccentric`, `lower-isometric`,
  `lower-power`, `upper-body`, `full-body`, `strength-endurance`
- **plyometrics:** `extensive`, `intensive`
- **running:** `easy-long`, `intervals`, `tempo-threshold` *(kept for the future;
  not proposed unless the athlete asks — see "Who this is tuned for")*

`gym/full-body` (all-round strength) and `gym/strength-endurance` (stair machine /
loaded vertical, blending endurance and strength) are the newest leaves, added
for this athlete's stated need for varied lower-body stimulus and a ski-relevant
vertical-endurance option.

Several leaves also carry a `> **This athlete —** …` note in the body where the
personalisation is session-specific (running deprioritisation, the plyometric
return-to-load, the cycling trainer/easy focus, the climbing swap for upper body).
The always-in-context `reference/catalog.md` encodes the running "only on request"
rule directly in those rows' descriptions.

Climbing (an `gym/upper-body` swap) and hiking/mountaineering (closest proxy:
`gym/strength-endurance`, used only when a mountain trip is on the calendar) are
handled as notes rather than separate leaves for now — add a leaf per "Adding or
changing a session" if either becomes a distinct scheduling object.
