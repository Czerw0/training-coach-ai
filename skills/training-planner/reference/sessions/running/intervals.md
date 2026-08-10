---
name: intervals
category: running
description: Use when planning VO2max or speed running intervals — the highest-intensity running session; do it fresh, protect the 48–72 h either side, and never as the first hard session back. For this athlete, plan running ONLY on explicit request (knee); when running is requested, this and tempo-threshold are the priority modes.
load: {neural: high, mechanical: high, metabolic: high, damage: moderate}
residual_fatigue_h: 48
same_day_conflicts: [gym/lower-eccentric, gym/lower-power, plyometrics/intensive, running/tempo-threshold, cycling/intervals]
spacing_h: {running/tempo-threshold: 48, cycling/intervals: 48, gym/lower-eccentric: 72, gym/lower-power: 48, plyometrics/intensive: 48, running/easy-long: 24}
pairs_well_with: [running/easy-long, cycling/endurance, gym/upper-body, gym/lower-isometric]
prerequisites: [consistent easy running base, no active bone or tendon symptoms, thorough warm-up available]
contraindicated_if: [bone stress suspicion, unresolved DOMS in the legs, first two weeks back from a layoff, poor readiness]
see_also: [principles/load-and-recovery, principles/planning-the-week, running/tempo-threshold]
---

# Running — intervals

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

> **This athlete —** running is **not proposed unless the athlete explicitly asks
> for it** (knee injury; the agent should reach for `cycling/*` for hard aerobic
> work by default). When running *is* requested, this session and
> `running/tempo-threshold` are the two priority modes — they carry the training
> value the athlete wants from running, so protect them over easy volume. Return
> to running is capped hard by tissue tolerance (see Don't use when): reintroduce
> as short reps, never as the first hard session back.

## Use when

The highest-intensity running in the plan: VO2max intervals and faster speed
work. Highest return per session in running, and the highest injury exposure —
pace plus impact on tired legs is the classic mechanism.

Prescribe when the athlete has a stable easy-running base, is in a build or
competition phase, and today's readiness is good.

## Don't use when

- Readiness is poor. Downgrade to tempo, then easy, then rest — see the
  downgrade ladder in `principles/load-and-recovery`.
- There is unresolved lower-body soreness from gym or plyometric work.
- The athlete is in the first two weeks back from a layoff. Speed returns before
  tissue tolerance does; this is where comebacks break.
- Any suspicion of bone stress — focal bony tenderness, or pain that worsens
  through a run instead of warming up. That routes to a clinician, not to a
  modified session.

## Prescription

| Variant | Structure | Effort | Recovery | Use for |
|---|---|---|---|---|
| VO2max | 4–6 × 3–5 min | RPE 9, ~3–5 k race pace | near-equal easy jog | Aerobic power |
| Short VO2max | 8–12 × 60–90 s | hard, controlled | 60–90 s jog | Same stimulus, less strain |
| Speed / mechanics | 6–10 × 15–30 s | fast, relaxed | full (2–3 min) | Speed, coordination |
| Strides | 4–8 × 20 s | fast, submaximal | walk back | Sharpener, taper-safe |

**Warm-up is part of the prescription, not a preamble:** 10–15 min easy jog,
drills, 3–4 progressive strides. The first rep should not be the first fast
running of the day. Cool down 10 min easy.

**Session cap:** total hard running time of roughly 15–25 min for VO2max work.
Beyond that the last reps are slower than the first, which is a different (and
worse) session than the one prescribed.

## Dosing and progression

- **Add a rep, or add time per rep, before adding pace.** Pace is anchored to a
  recent race or test, not to ambition.
- **Hold the last rep as fast as the first.** If pace falls off, the session is
  finished — cutting it there is the correct call, not a failure.
- Progress the session **or** the week's volume, never both.
- **Regression path:** fewer reps → shorter reps with the same pace → tempo →
  easy run.

**On volume progression:** do not progress this session against a fixed weekly
percentage. Progress it against **the longest and hardest single session of the
previous 30 days** — that comparison predicts running injury; week-to-week
volume change does not (see `principles/load-and-recovery` §3).

## Scheduling

**Hard rules:**
- Fresh legs only: no heavy lower-body gym, plyometrics or another hard session
  in the preceding 48 h.
- ≥48 h from any other hard running or hard cycling session.
- Not the same day as anything in `same_day_conflicts`.
- Taper: volume drops, and only strides or short sharpeners remain.

**Preferences:**
- Mid-week, after a rest or easy day.
- Follow with an easy run or rest, not the long run.
- Pair the surrounding days with upper body, isometrics, or Z2 cycling.

**What it costs the next 48 h:** high on three axes at once — this is the most
expensive session in the library per minute. The day after is easy or nothing.

## Interactions

- **With `cycling/intervals`:** both are the week's hard aerobic session.
  One of each per week is the sensible ceiling for most athletes; two hard
  running days plus a hard ride is where the week stops being recoverable.
- **With `plyometrics/*`:** intensive plyos and interval running load the same
  tissues at the same intensity. Keep 48 h apart. Extensive plyos are fine as
  movement prep in the same warm-up.
- **With `gym/lower-max-strength`:** 24 h is workable if the run comes first in
  the pairing across days. Running interferes with strength adaptation more than
  cycling does — if the athlete's lifting has stalled, this is why.
- **With `cycling/endurance`:** the best day-after option. Aerobic flush without
  impact.

## Stop rules

- Pace falling off across reps → session over, cool down.
- Any new sharp pain, or pain that changes the athlete's gait → stop running,
  walk home.
- Pain that worsens as the run progresses (rather than easing after the
  warm-up) → stop, and route to a clinician before the next running session.
- Dizziness, chest symptoms or disproportionate breathlessness → stop.

## Worked example

> **Context:** club runner, 10 k goal in 8 weeks, 50 km/week, long run Sunday,
> tempo Thursday, gym Monday. Slept badly two nights running, HRV down but
> within the 7-day band.

> **Prescription — Tuesday:**
> - Warm-up: 15 min easy, drills, 4 × 20 s strides
> - Main: 5 × 3 min @ RPE 9 (~3 k effort), 2:30 easy jog recovery
> - Cool-down: 10 min easy
> - Total hard time: 15 min

> **Placement rationale:** Tuesday sits 48 h from Thursday's tempo and 72 h from
> Monday's gym session. Chosen 5 × 3 min rather than 5 × 4 min because two poor
> nights of sleep with HRV drifting down is a reason to take the conservative
> end of the range — not to cancel, since the trend is still inside the normal
> band. Wednesday is easy running only.

## Evidence notes

**Supported:**
- Endurance performance improves under both polarized and pyramidal intensity
  distributions, with polarized showing a small pooled advantage for VO2peak.
  Interval work is the "hard" pole in either model.
- Single-session distance relative to the longest run in the previous 30 days
  predicts running injury; weekly mileage change performs no better than chance,
  and neither the 10% rule nor ACWR should be used to plan running progression.
- Adding strength and plyometric work to running improves economy durability and
  fatigued high-intensity performance — worth citing when justifying why gym
  sessions sit in a runner's week at all.

**Convention:**
- The 48–72 h spacing figures.
- The 15–25 min cap on hard running time. A widely used coaching heuristic that
  matches the intensities involved, not a tested threshold.
