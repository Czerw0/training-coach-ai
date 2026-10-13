---
name: upper-body
category: gym
description: Use when planning an upper-body strength or hypertrophy session (push, pull, press) — the most schedule-flexible gym day; legs are spared so it barely competes with endurance work.
load: {neural: moderate, mechanical: low, metabolic: low, damage: low}
residual_fatigue_h: 24
same_day_conflicts: []
spacing_h: {gym/upper-body: 48}
pairs_well_with: [cycling/endurance, running/easy-long, running/intervals, cycling/intervals, running/tempo-threshold, gym/lower-power, plyometrics/intensive]
prerequisites: [competent pressing and pulling technique under load]
contraindicated_if: [acute shoulder, elbow or wrist injury aggravated by loading]
see_also: [principles/planning-the-week, gym/lower-max-strength]
---

# Gym — upper body

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

## Use when

Training the upper body — horizontal/vertical push and pull, direct arm and
shoulder work. Because the legs are spared, this is the **lowest-interference
gym day** and the most schedule-flexible session in the library: it slots in the
day before or after hard running or cycling without stealing from either. Reach
for it to keep an athlete training while protecting the legs for a key endurance
or lower-body session.

## Don't use when

- An upper-limb injury is reactive and loading is painful — swap to a pain-free
  variation or a different day, don't train through it.
- It would crowd out a key lower-body or endurance session on a tight week;
  upper body is a shock absorber, not a priority slot.

## Prescription

| Variant | Sets × reps | Intensity | Rest | Use for |
|---|---|---|---|---|
| Strength | 3–5 × 3–6 | ~80–90% 1RM, RPE 7–9 | 2–4 min | Force, neural drive |
| Hypertrophy | 3–4 × 6–12 | ~67–80% 1RM, RPE 7–9, ~2 RIR | 60–120 s | Muscle mass |

**Session shape:** one or two compound lifts first (bench / overhead press /
row / pull-up / dip), then 1–3 accessories where freshness matters less.

## Dosing and progression

- **Double progression:** hold the rep range, add reps weekly across sets; once
  the top of the range is hit on all sets, add load and return to the bottom.
- Pull `get_exercise_detail` for any lift when a shoulder, elbow or wrist injury
  is active, and substitute a pain-free variation.
- **Regression path:** reduce load → reduce range → swap to a machine or
  supported variation.

## Scheduling

**Hard rules:**
- None that constrain the rest of the week — this is the freely-placed session.

**Preferences:**
- ~48 h before hammering the same muscle groups hard again; lighter overlapping
  accessories between are fine.
- Ideal on days the athlete must protect the legs for a key endurance session
  but still wants to train.
- Pairs cleanly with any endurance or lower-body day.

**What it costs the next 24 h:** little that affects running or cycling —
moderate neural cost locally, negligible on the legs.

## Interactions

- **With `running/*` and `cycling/*`:** minimal leg overlap, so it schedules
  freely around them, including the day before or after a hard session.
- **With lower-body gym:** independent muscle groups; can share a day or sit
  adjacent without a spacing concern.

## Stop rules

- Sharp joint pain in a shoulder, elbow or wrist during a rep — end the exercise.
- Technique breakdown under load — the set ends, the next set drops weight.
- A tendon reading above ~3/10, or worse the next morning.

## Worked example

> **Context:** runner in a build block, hard intervals Tuesday, long run
> Saturday, wants to keep pressing/pulling strength without touching the legs.

> **Prescription — Thursday (between the two key run days):**
> - A. Bench press — 4 × 5 @ RPE 8
> - B. Weighted pull-up — 4 × 5
> - C. Seated DB shoulder press — 3 × 8
> - D. Face pull + curl superset — 3 × 12
> - Optional easy spin later for aerobic volume.

> **Placement rationale:** Thursday sits between Tuesday's intervals and
> Saturday's long run. Upper body loads none of the tissue those sessions need,
> so it adds training without costing either — exactly the shock-absorber role.

## Evidence notes

**Supported:**
- Concurrent endurance work does not meaningfully blunt upper-body strength or
  hypertrophy; the interference effect that matters is lower-body power (see
  `principles/load-and-recovery` §2). This session is effectively free of it.

**Convention:**
- The 48 h same-muscle spacing and the RPE/%1RM anchors — standard, useful, not
  derived from a specific trial.
