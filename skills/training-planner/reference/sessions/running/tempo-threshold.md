---
name: tempo-threshold
category: running
description: Use when planning tempo or threshold running (continuous or cruise intervals) — a key day, less taxing than full VO2max intervals; keep 48 h from other hard running or cycling.
load: {neural: moderate, mechanical: moderate, metabolic: high, damage: moderate}
residual_fatigue_h: 48
same_day_conflicts: [gym/lower-eccentric, gym/lower-power, gym/lower-max-strength, plyometrics/intensive, running/intervals, cycling/intervals]
spacing_h: {running/intervals: 48, cycling/intervals: 48, running/tempo-threshold: 48, gym/lower-eccentric: 72}
pairs_well_with: [running/easy-long, cycling/endurance, gym/upper-body, gym/lower-isometric]
prerequisites: [easy running base, no active bone or tendon symptoms, warm-up available]
contraindicated_if: [bone stress suspicion, unresolved DOMS, poor readiness, first two weeks back from a layoff]
see_also: [principles/load-and-recovery, running/intervals]
---

# Running — tempo & threshold

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

## Use when

Sustained "comfortably hard" running to lift the lactate threshold: continuous
tempo, or threshold cruise intervals. A key day with high metabolic return — and
genuinely less taxing than full VO2max intervals, which is what makes it the
threshold workhorse of a build block.

Prescribe when the athlete has a stable easy-running base, no bone or tendon
symptoms, and today's readiness is reasonable.

## Don't use when

- Readiness is poor — downgrade to easy running, then rest
  (`principles/load-and-recovery` §4).
- There is unresolved DOMS in the legs from gym or plyometric work.
- The athlete is in the first two weeks back from a layoff — threshold pace
  returns before tissue tolerance does.
- Any bone-stress suspicion. That routes to a clinician, not a shortened tempo.

## Prescription

| Variant | Structure | Effort | Recovery | Use for |
|---|---|---|---|---|
| Continuous tempo | 20–40 min | RPE 7–8, threshold pace | — | Sustainable threshold, mental toughness |
| Cruise intervals | 3–5 × 5–8 min | threshold | 60–90 s jog | More threshold time at slightly lower strain |
| Progression finish | easy → 10–15 min @ threshold | builds to RPE 7–8 | — | Teaching pacing on tired legs |

**Threshold pace** is roughly the fastest pace holdable for about an hour —
controlled breathing, working but not gasping. Warm-up (10–15 min easy) and
cool-down (10 min easy) are part of the session, not optional.

## Dosing and progression

- **Add time-at-threshold before pace.** A longer continuous block, or an extra
  cruise rep, is a real progression; chasing faster pace turns tempo into a VO2
  session it wasn't meant to be.
- Anchor pace to a **recent threshold test or race**, not to ambition.
- Progress the session **or** the week's running volume, never both; progress
  the hard session against the prior 30-day ceiling, not a weekly percentage
  (`principles/load-and-recovery` §3).
- **Regression path:** shorten the tempo → cruise intervals with more jog
  recovery → easy run → rest.

## Scheduling

**Hard rules:**
- ≥48 h from other hard running or hard cycling; ≥72 h from eccentric leg work.
- Not the same day as anything in `same_day_conflicts`.
- Followed by an easy or rest day.
- Taper: keep only short threshold minutes, not full tempo loads.

**Preferences:**
- Mid-week, after a rest or easy day, on reasonable readiness.
- Pair the surrounding days with easy running, Z2 cycling, upper body or
  isometrics.
- If the week already holds a hard ride and hard intervals, this is usually one
  hard aerobic session too many — pick the two that serve the block's goal.

**What it costs the next 48 h:** high `metabolic`, moderate `mechanical` and
`damage`. Less brutal than VO2max intervals per minute, but still a key day that
earns an easy day after.

## Interactions

- **With `running/intervals`:** both are hard running; 48 h apart, and rarely
  both plus a hard ride in the same week (`principles/planning-the-week` §2).
- **With `cycling/intervals`:** same 48 h aerobic-intensity spacing — they draw
  on the same recovery even though the tissue cost differs.
- **With `running/easy-long`:** complementary — easy running and the long run
  are the low-intensity frame this hard session sits inside.
- **With `gym/lower-isometric` / `gym/upper-body`:** clean pairings that don't
  add impact or soreness to threshold-loaded legs.

## Stop rules

- Pace drifting well off threshold with breathing spiking → the session has
  become a VO2 effort; ease back to true threshold or end it.
- New sharp pain, or pain that changes gait → stop running, walk home.
- Pain worsening across the run rather than easing after the warm-up → stop, and
  route a bone-stress suspicion to a clinician.
- Disproportionate breathlessness, chest symptoms or dizziness → stop.

## Worked example

> **Context:** half-marathon build, 5 runs/week, long run Sunday, gym (upper +
> isometrics) Monday. Readiness normal. Wants a threshold session that doesn't
> compromise Sunday's long run.

> **Prescription — Wednesday:**
> - Warm-up 15 min easy + 4 × 20 s strides
> - Main: 4 × 6 min @ threshold (RPE 7–8), 75 s jog between
> - Cool-down 10 min easy

> **Placement rationale:** Wednesday sits ≥72 h from Sunday's long run and clear
> of Monday's gym (which was upper/isometric anyway, so no leg clash). Cruise
> intervals rather than a 35 min continuous block because they bank the same
> threshold time at slightly lower strain, protecting the weekend. Thursday is
> easy running; a hard ride this week would break the 48 h aerobic-intensity
> spacing, so it isn't planned.

## Evidence notes

**Supported:**
- Threshold/tempo work is the middle-intensity zone in a pyramidal distribution
  and a small but real component of a polarized one; both distributions are
  effective, with most volume low-intensity (`principles/planning-the-week` §1).
- Progressing hard running against the previous 30-day peak session — not a
  weekly percentage — is the better-founded approach to running-load progression
  (`principles/load-and-recovery` §3).

**Convention (defaults, thinly evidenced):**
- The 20–40 min tempo and 3–5 × 5–8 min cruise structures, and the 48–72 h
  spacing figures. Standard coaching prescriptions matched to the intensity, not
  validated thresholds — anchor pace to the athlete's own tested threshold.
