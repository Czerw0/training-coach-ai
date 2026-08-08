---
name: intervals
category: cycling
description: Use when planning hard cycling — VO2max, threshold or sweetspot; high metabolic cost but no impact, so it recovers faster than hard running while still being a key day.
load: {neural: moderate, mechanical: low, metabolic: high, damage: moderate}
residual_fatigue_h: 48
same_day_conflicts: [gym/lower-eccentric, gym/lower-power, gym/lower-max-strength, plyometrics/intensive, running/intervals, running/tempo-threshold]
spacing_h: {running/intervals: 48, cycling/intervals: 48, running/tempo-threshold: 48, gym/lower-eccentric: 48}
pairs_well_with: [gym/upper-body, gym/lower-isometric, cycling/endurance]
prerequisites: [aerobic base, no active illness]
contraindicated_if: [poor readiness, systemic illness]
see_also: [principles/load-and-recovery, principles/planning-the-week, cycling/endurance]
---

# Cycling — intervals

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

## Use when

The hard cycling day: raising FTP, VO2max or repeatability. High return at high
metabolic cost — but, unlike hard running, almost no impact. That combination
makes it a key session that recovers faster than its perceived effort suggests
(low `mechanical`, high `metabolic`), so it can sit a little closer to the rest
of the week than a hard run of similar strain.

Prescribe when the athlete has an aerobic base, no illness, and today's
readiness is good.

## Don't use when

- Readiness is poor. Downgrade sweetspot → Z2, or VO2max → sweetspot → Z2, per
  the ladder in `principles/load-and-recovery` §4.
- The athlete has systemic illness symptoms.
- It would land the same day as heavy or hard leg work — the interval quality
  and the leg session both suffer.

## Prescription

| Variant | Structure | Intensity | Recovery | Use for |
|---|---|---|---|---|
| Sweetspot | 3 × 15–20 min | 88–94% FTP | 5 min easy | Big fitness-per-strain; a good default hard day |
| Threshold | 2–4 × 8–20 min | 88–100% FTP | 4–5 min easy | Sustainable power at FTP |
| VO2max | 4–6 × 3–5 min | 106–120% FTP | near-equal easy | Aerobic power; the most taxing — good-readiness days |
| Indoor (any) | prescribed by watts off current FTP | — | — | Pull `get_workout_detail` for a matching workout |

**Warm-up is part of the session:** a progressive build before the first hard
effort — the athlete should not hit interval one cold. Cool down easy.

## Dosing and progression

- **Add time-at-intensity before intensity.** A longer sweetspot block or an
  extra threshold rep is a real progression; jumping straight to VO2max power is
  not.
- Anchor targets to a **current, tested FTP** and re-test periodically — stale
  FTP turns "threshold" into either junk or over-reach.
- Progress the session **or** the week's volume, not both.
- **Regression path:** VO2max → threshold → sweetspot → Z2 endurance.

## Scheduling

**Hard rules:**
- Not the same day as anything in `same_day_conflicts` (heavy/hard legs, hard
  running).
- ≥48 h from other hard aerobic sessions (cycling or running intervals, hard
  running tempo).
- Followed by an easy or rest day.

**Preferences:**
- Mid-week on a good-readiness day, after a rest or easy day.
- Pairs cleanly the day before or after upper-body or isometric leg work —
  cycling doesn't load the tissue those stress.
- One hard ride plus one hard run per week is the sensible aerobic-intensity
  ceiling for most athletes.

**What it costs the next 48 h:** high `metabolic`, moderate `damage`, no impact.
Legs feel emptied rather than pounded — a Z2 ride the next day is fine, a hard
run is not.

## Interactions

- **With `running/intervals` and `running/tempo-threshold`:** both are the
  week's hard aerobic work. Keep 48 h between; two hard runs plus a hard ride is
  where the week stops being recoverable (`principles/planning-the-week` §2).
- **With `gym/lower-isometric` and `gym/upper-body`:** among its best pairings —
  no impact competition, no soreness clash.
- **With `gym/lower-eccentric`:** keep 48 h — sore legs degrade interval power,
  and the metabolic session offers the legs no recovery.
- **When downgraded for readiness:** it becomes `cycling/endurance` — same day,
  same slot, a fraction of the cost.

## Stop rules

- Power unable to reach target at normal RPE, or dropping across reps → the
  session is over or should become Z2; treat it as a readiness signal.
- Systemic illness symptoms → no session.
- Chest symptoms, dizziness or disproportionate breathlessness → stop.
- Knee pain appearing during pedalling → stop and check fit/cleats before
  prescribing more intensity.

## Worked example

> **Context:** time-crunched cyclist, build phase, key sessions are a Wednesday
> hard ride and a Saturday long ride. Monday was an upper-body gym day. Readiness
> good, no illness.

> **Prescription — Wednesday:**
> - Warm-up 15 min progressive, 2 × 1 min openers
> - Main: 3 × 15 min sweetspot @ 90% FTP, 5 min easy between
> - Cool-down 10 min easy
> - Targets set off last month's FTP test.

> **Placement rationale:** Wednesday sits ≥48 h from Saturday's long ride and
> clear of any leg-gym day. Sweetspot rather than VO2max because two key aerobic
> sessions already sit in the week and sweetspot returns most of the fitness for
> less recovery cost. Thursday is Z2 or rest; a hard run this week would break
> the 48 h aerobic-intensity spacing, so it isn't planned.

## Evidence notes

**Supported:**
- Endurance performance improves under both polarized and pyramidal intensity
  distributions; interval work is the "hard" pole in either. Most weekly volume
  should still be low-intensity (`principles/planning-the-week` §1).
- Cycling's lack of impact means it carries hard metabolic work at far lower
  bone/tendon cost than equivalent running — the basis for substituting a hard
  ride when running impact must be capped.

**Convention (defaults, thinly evidenced):**
- The specific FTP bands (88–94% sweetspot, 88–100% threshold, 106–120% VO2max)
  and the 48 h spacing figures. Standard, useful, and model-dependent — anchor
  to the athlete's own tested FTP rather than a generic table.
