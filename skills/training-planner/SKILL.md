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
  {"id": "running/intervals",      "start": "2026-08-15T10:00"}
]
```

It prints violations as JSON (or `--format text`) and exits non-zero if any are
`error`-severity, so it doubles as a gate. Severity is the whole point:
`error` = the plan is wrong, fix it; `warning` = a defensible compromise you
must state rather than bury. Design decisions (spacing direction, which number
wins on disagreement, the per-axis saturation windows) are documented at the top
of the file.

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

Migrated leaves: `cycling/endurance`, `gym/lower-max-strength`,
`gym/lower-eccentric`, `plyometrics/intensive`, `running/intervals`. Their
frontmatter also references sibling sessions that share the same design
(`gym/upper-body`, `gym/lower-isometric`, `gym/lower-power`,
`plyometrics/extensive`, `cycling/intervals`, `running/easy-long`,
`running/tempo-threshold`) — those cross-references stay valid, and each becomes
a full leaf the moment its file is added, per "Adding a session" above.
