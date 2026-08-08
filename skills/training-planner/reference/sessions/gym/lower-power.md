---
name: lower-power
category: gym
description: Use when planning explosive lower-body strength (jumps, speed squats, Olympic variants) — low reps at full recovery, quality over fatigue; the session interference genuinely threatens, so protect its freshness.
load: {neural: high, mechanical: moderate, metabolic: low, damage: low}
residual_fatigue_h: 48
same_day_conflicts: [gym/lower-max-strength, gym/lower-eccentric, plyometrics/intensive, running/intervals, running/tempo-threshold, cycling/intervals]
spacing_h: {gym/lower-max-strength: 48, gym/lower-eccentric: 72, plyometrics/intensive: 48, running/intervals: 48, gym/lower-power: 48}
pairs_well_with: [gym/upper-body, cycling/endurance]
prerequisites: [strength base from gym/lower-max-strength, sound landing mechanics]
contraindicated_if: [no strength base, poor readiness, active lower-limb injury]
see_also: [principles/load-and-recovery, plyometrics/intensive, gym/lower-max-strength]
---

# Gym — lower body, power

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

## Use when

Training the legs to produce force **fast**: jump squats, trap-bar jumps,
Olympic-lift variations (power clean/pull, hang variants), speed squats moved
with maximal intent, or contrast/PAP pairs. The aim is peak output and bar or
jump velocity — never fatigue.

This is one of only two sessions (with `plyometrics/intensive`) where the
interference effect is genuinely worth planning around: explosive and power
qualities are exactly what concurrent endurance work can blunt
(`principles/load-and-recovery` §2). Protect its freshness accordingly.

## Don't use when

- The athlete has no strength base. Power work amplifies force the legs can
  already produce; build it in `gym/lower-max-strength` first.
- Readiness is poor, or there is lingering lower-body soreness. A fatigued power
  session trains slow, fatigued movement — the opposite of the goal.
- Landing mechanics are not sound. Speed under bad positions is an injury route,
  not a training stimulus.

## Prescription

Pick 1–2 movements. Every rep is maximal-intent and fast, or the set is over.

| Variant | Sets × reps | Load / intent | Rest | Notes |
|---|---|---|---|---|
| Jump squat / trap-bar jump | 3–5 × 3–5 | bodyweight → light, max height | 2–3 min | Full recovery; height, not fatigue |
| Speed squat | 3–5 × 2–4 | ~30–60% 1RM, maximal velocity | 2–3 min | Stop when bar speed drops |
| Olympic-lift variant | 3–5 × 2–3 | technical, explosive | 2–4 min | Only with competent technique |
| Contrast / PAP pair | 3–4 × (heavy 2–3 + explosive 3–5) | heavy set, then explosive a few min later | 3–4 min | Advanced; fresh legs only |

**Session shape:** low total volume, long rests. Quality is the whole session —
this is not conditioning and should never leave the athlete out of breath.

## Dosing and progression

- **Progress output, not fatigue.** Add jump height, add load while holding
  velocity, or add a set — never add grindy reps.
- Track velocity where possible; a noticeable drop within a set means that set
  is done, and repeated drops across the session mean the session is done.
- Introduce complexity before intensity: bilateral before unilateral, submaximal
  before maximal loads on the speed work.
- **Regression path:** reduce reps/height → drop to `plyometrics/extensive` for
  elastic quality → technique work at moderate load in `gym/lower-max-strength`.

## Scheduling

**Hard rules:**
- Fresh legs only: nothing heavy or hard on the legs in the preceding 48 h.
- ≥48 h from heavy lower-body strength, hard running/cycling and other power
  work; ≥72 h from eccentric leg work.
- Not the same day as anything in `same_day_conflicts`.
- First in the session, straight after a full warm-up — never after conditioning
  or endurance.

**Preferences:**
- Early in the week and early in the session, on a good-readiness day.
- Pair the following day with upper body or Z2 cycling.
- Can serve as a short potentiation primer *before* sprint/speed work on a
  dedicated fresh-legs day.

**What it costs the next 48 h:** high `neural`, low `damage`. It feels cheap —
tiny volume, no soreness, no breathlessness — and that mismatch is exactly why
it gets misplaced onto tired legs. Treat the neural cost as real.

## Interactions

- **With `plyometrics/intensive`:** overlapping neural demand and the same
  freshness requirement. Either keep them 48 h apart, or combine into one
  "fresh legs" day — power first, plyos second, total volume cut.
- **With `gym/lower-max-strength`:** its prerequisite and its worst same-day
  partner. Heavy strength fatigue destroys the velocity this session trains;
  keep 48 h between them.
- **With `cycling/endurance`:** the safe day-after option — low mechanical
  strain, no competition for the trained quality.
- **Interference:** power and explosive strength are where the interference
  effect is genuinely supported. This is a session to protect from surrounding
  hard endurance work, unlike strength or hypertrophy days that schedule freely.

## Stop rules

- Bar or jump velocity dropping across a set → the set is over; that is fatigue,
  not a rep to fight for.
- Any loss of landing control — knees caving, heavy or asymmetric landings →
  stop the exercise, regress next session.
- Sharp joint, tendon or muscle pain → end the session; do not substitute
  another explosive movement in its place.
- Poor readiness discovered in the warm-up (flat, slow, heavy) → downgrade to
  isometrics or easy aerobic rather than forcing a low-quality power session.

## Worked example

> **Context:** cyclist-turned-sprint-triathlete, build phase, 3 months of
> consistent lower-body strength (squats ~1.5× bodyweight), sound landings,
> good readiness today. Key intensity is Thursday's cycling intervals; long
> ride Saturday.

> **Prescription — Monday, after full warm-up, first thing:**
> - Trap-bar jump — 4 × 3, max height, 2.5 min rest
> - Speed squat — 4 × 3 @ 40% 1RM, maximal velocity, 2.5 min rest
> - Pogo primer beforehand (2 × 10, from `plyometrics/extensive`)
> - Total working reps kept low; any slow rep ends the set.

> **Placement rationale:** Monday follows Sunday rest, so the legs are as fresh
> as the week allows, and it sits ≥48 h before Thursday's hard ride. Chosen over
> a same-day pairing with strength because heavy fatigue would blunt the very
> velocity being trained. Tuesday is Z2 cycling — a safe day-after that doesn't
> compete for the trained quality.

## Evidence notes

**Supported:**
- The interference effect **is** real for power and explosive-strength outcomes,
  even where it is absent for maximal strength and hypertrophy — so protecting
  this session's freshness from concurrent endurance work is evidence-based, not
  just cautious.
- A strength base underpins expressible power: adding heavy strength and
  power/plyometric work improves economy and fatigued high-intensity performance
  in endurance athletes.
- Velocity-based control (stopping as bar speed drops) limits neuromuscular
  fatigue while preserving the power stimulus.

**Convention (defaults, thinly evidenced):**
- The 48 h spacing from strength/intervals and 72 h from eccentric work — a
  reasonable read of neural recovery, not a tested threshold.
- The specific 30–60% 1RM speed-squat band. A standard coaching range; the real
  gate is maximal intent and maintained velocity, not the exact percentage.
