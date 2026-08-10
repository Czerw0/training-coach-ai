---
name: easy-long
category: running
description: Use when planning easy aerobic runs or the weekly long run — easy runs are near-free; the long run is the week's key running stressor and needs real recovery and distance from heavy-leg work. For this athlete, DEPRIORITIZED (knee) — only on explicit request, and cycling/endurance is the default easy-aerobic substitute; running priority when requested is intervals + tempo-threshold.
load: {neural: low, mechanical: moderate, metabolic: moderate, damage: moderate}
residual_fatigue_h: 24
same_day_conflicts: []
spacing_h: {running/intervals: 24, gym/lower-eccentric: 48, plyometrics/intensive: 24}
pairs_well_with: [gym/upper-body, gym/lower-isometric, cycling/endurance]
prerequisites: [no active bone stress]
contraindicated_if: [bone-stress suspicion, systemic illness]
see_also: [principles/planning-the-week, running/intervals, running/tempo-threshold]
---

# Running — easy & long

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

> **This athlete —** **deprioritized.** Running is not proposed unless the athlete
> asks, and even then easy/long running is *not* the point — the knee tolerates
> impact volume poorly, and `cycling/endurance` is the default easy-aerobic
> substitute (same aerobic stimulus, a fraction of the impact). Keep this session
> in the library because the athlete plans to run more in future; when running is
> requested now, the priority is `running/intervals` and `running/tempo-threshold`,
> with easy running only as a minimal base/recovery frame around them.

## Use when

Two modes share this file because they share a tissue and a discipline, but they
sit at opposite ends of the cost scale:

- **Easy runs** — frequent, conversational aerobic running. Near-free: the
  cheapest way to hold running frequency and tissue tolerance.
- **The long run** — the week's key running endurance stressor. This one is a
  key session and must be scheduled like one.

Running costs more impact per aerobic minute than cycling, so even easy running
needs more care with volume progression than a Z2 ride.

## Don't use when

- There is a bone-stress suspicion — focal bony tenderness, or pain that worsens
  through a run rather than warming up. That routes to a clinician, not a
  modified run.
- Systemic illness symptoms are present.
- For the **long run specifically:** it can't get its easy day after, or it
  would sit within 48 h of heavy-leg gym / intensive plyos. Easy runs carry no
  such restriction.

## Prescription

| Variant | Duration | Intensity | Notes |
|---|---|---|---|
| Recovery run | 20–40 min | very easy, Zone 1–2 | Day after a hard session; optional over rest |
| Standard easy | 30–60 min | conversational, Zone 2, RPE 3–4 | The bulk of weekly running |
| Long run | building duration/distance | Zone 2, aerobic throughout | The week's key running stressor |
| Long run + finish | as above + short goal-pace block | easy, then brief tempo at the end | Only once base distance is solid |

**Discipline:** easy means easy. The commonest failure is easy runs drifting up
into the grey zone, which quietly turns cheap volume into a cost the next day
(`principles/planning-the-week` §1).

## Dosing and progression

- **Grow frequency first, then the long run, then total volume.** Frequency
  distributes the same load across more, smaller exposures.
- **Progress the long run against its own 30-day ceiling**, not against last
  week's weekly total — single-session spikes over ~10% of the longest run in
  the prior 30 days are what predicts running injury
  (`principles/load-and-recovery` §3). Deload the long run periodically rather
  than ratcheting it every week.
- Add duration or frequency before adding pace; keep goal-pace finishes small
  and rare until base distance is established.
- **Regression path:** long run → standard easy → recovery run → cross-train
  (`cycling/endurance`) → rest.

## Scheduling

**Hard rules:**
- **Long run:** needs an easy or rest day after it, and ≥48 h from eccentric leg
  work; don't chain it into hard intervals.
- Any bone-stress suspicion removes the session entirely.

**Preferences:**
- **Easy runs:** near-free — fine the day after intensity as a flush, or paired
  with an upper-body/isometric gym day. No same-day conflict.
- Treat a long run over ~2.5–3 h like a key session with a real recovery
  requirement, not as "just easy miles."
- Keep the long run and heavy lower-body gym / intensive plyos apart — the legs
  can't absorb both well.

**What it costs:** easy runs are low and clear within a day; the long run's
`damage` and `mechanical` cost is real and rises steeply with duration. Higher
impact per aerobic minute than any cycling session.

## Interactions

- **With `running/intervals`:** 24 h is workable only easy-run → intervals with
  the easy run genuinely easy; the long run needs more clearance.
- **With `cycling/endurance`:** the standard swap when running impact must be
  capped — a Z2 ride keeps the aerobic stimulus at a fraction of the impact.
- **With `gym/upper-body` / `gym/lower-isometric`:** clean pairings; neither
  competes for impact-loaded tissue.
- **With `gym/lower-eccentric` / `plyometrics/intensive`:** keep the long run
  clear — running loads exactly the tissue those sessions have already stressed.

## Stop rules

- New sharp pain, or pain that changes gait → stop running, walk home.
- Pain that worsens as the run progresses rather than easing after the warm-up →
  stop, and route a bone-stress suspicion to a clinician before the next run.
- On an easy run, an inability to hold a conversational effort at normal pace →
  treat as a readiness signal; shorten and reconsider the week.
- Dizziness, chest symptoms or disproportionate breathlessness → stop.

## Worked example

> **Context:** club runner, 10 k build, 50 km/week, long run Sunday, intervals
> Tuesday, gym Monday. Wants to add an easy midweek run without disturbing the
> two key sessions.

> **Prescription — this week:**
> - Wednesday: standard easy, 45 min Zone 2, RPE 3–4
> - Friday: recovery easy, 30 min, day before the long run kept genuinely light
> - Sunday: long run, building to 95 min aerobic (last week 90 min — under the
>   30-day-ceiling step)
> - Monday after: upper body + easy spin, legs protected

> **Placement rationale:** the two easy runs are near-free and slot around the
> key days without conflict. Friday stays short precisely because Sunday's long
> run is a key session that needs fresh-ish legs. The long run progresses ~5–6%
> on its own recent ceiling rather than by a weekly-mileage rule, and Monday is
> deliberately non-impact to respect the long run's residual cost.

## Evidence notes

**Supported:**
- Most endurance volume should be low-intensity under both polarized and
  pyramidal models — this session is that bulk.
- **Single-session distance relative to the longest run in the previous 30 days
  predicts running injury; weekly-mileage change performs no better than
  chance**, and neither the 10% rule nor ACWR should drive running progression
  (`principles/load-and-recovery` §3).
- Running carries more impact per aerobic minute than cycling — the rationale
  for substituting easy rides when bone/tendon load must be capped.

**Convention (defaults, thinly evidenced):**
- The ~2.5–3 h "treat as a key session" long-run threshold and the 24/48 h
  spacing figures. Reasonable coaching defaults, not tested thresholds.
