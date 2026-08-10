---
name: planning-the-week
kind: principles
description: Intensity distribution, the order in which a week gets built, deloads, tapers and return-to-load. Read before writing any multi-session plan.
---

# Principles — building the week

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

Read `principles/load-and-recovery` first — this file assumes the four fatigue
axes and the interference rules from it.

## 0. This athlete — priorities, structure and season

The generic principles below still hold; this section is the standing context
they get applied within. It is the first thing to load when planning a week.

**North star: skiing.** Skiing is the main sport and the winter goal. It is
**not trained inside this system** — it happens on-snow, in season. Everything
here is summer/shoulder-season preparation, so **every session should be
justifiable by its transfer to winter ski performance and to long-term gains,
not short-term numbers.** When two options are close, pick the one that serves
the ski goal and the athlete's durability over the one that flatters a weekly
metric.

**Current priorities:** cycling, gym, plyometrics. Cycling is the second main
sport and the default aerobic engine. **Running is not proposed unless the
athlete explicitly asks** (knee) — default to `cycling/*` for aerobic work; see
the `running/*` leaves for how to handle it when requested.

**Plan around injuries and schedule first — flexibility is a feature, not a
fallback.** The immovables in step 2 below are, for this athlete, primarily
*current injury status* and *life/schedule*, not races. Re-plan freely as those
change; a rigid week is the wrong output here.

**Standing healthy-week shape (when uninjured):**
- **~2× cycling** (flexes **1–2×** with time, weather, injuries and other
  activity) — currently easy/consistent riding, not big volume.
- **~2× lower-body gym**, deliberately **rotating the type** across a block —
  `gym/lower-max-strength`, `gym/lower-eccentric`, `gym/lower-isometric`,
  `gym/lower-power`, plus the newer `gym/full-body` and `gym/strength-endurance`.
  Variety of stimulus is a stated goal, not a nice-to-have.
- **~1× upper-body gym** (`gym/upper-body`), swappable for a **climbing** session.
- **A lower-gym slot can be replaced by plyometrics or by
  `gym/strength-endurance`** (stair machine / loaded vertical) to blend endurance
  with strength.
- **1–3 rest days** per week is the normal range.
- Optional extra movement (volleyball, casual activity) may happen but is **not
  counted as a training session** — don't plan load around it, just note it as
  fatigue if it was significant.
- **When a week is cycling-primary, ease the lower-body gym** (submaximal loads,
  fewer hard leg sessions) so the strength work supports the riding rather than
  competing with it.

**Seasonal periodization (ski-focused annual arc).** Phase drives what a "good
week" looks like; state which phase a plan is in.

| Phase | Months | Primary focus | Endurance | Strength / power |
|---|---|---|---|---|
| Base | Apr–Jul | Endurance base | Primary, building volume | Early-block strength, then maintain |
| **Strength build** | **Aug–Sep (now)** | **Strength for skiing** | Moderate/hard, consistent — hold aerobic base, don't chase km | Build — the priority; plus a little aerobic |
| Pre-season power | Oct | Convert strength → power/speed | Reduced, easy | Transfer the Aug–Sep strength base into power and speed — `gym/lower-power`, plyometrics; sharpen, don't keep grinding max-strength |
| Pre-season down | Nov | Arrive fresh for snow | Light | Still a slight improvement, not a full taper — reduce load to be fresh |
| Ski season | Dec–Mar | Skiing (very hard, on-snow) | Consistency, can be the main aerobic work | **Maintain, not progress** — low-volume/isometric strength; don't accumulate fatigue that compromises ski days |

> **Current caveat (2026):** training was disrupted by illness/injury in June–July,
> so the aerobic base is **below its usual level right now** — do not benchmark
> against pre-illness fitness. Rebuild **consistency and frequency first** (see
> §7, Returning to load) before adding volume or intensity, even though the
> calendar phase is "strength build".

## 1. Intensity distribution

Most endurance training should be easy, and the hard part should be genuinely
hard. Two distributions dominate among well-trained athletes:

- **Polarized** — roughly 75–80% low intensity, ~5% threshold, 15–20% high
  intensity. Pooled evidence favours it for VO2peak, though the effect is small.
- **Pyramidal** — most volume low, then a decreasing amount of threshold, then
  least at high intensity. This is what elite endurance athletes actually log
  across a full season more often than not.

Both work; neither is universally superior. The useful pattern is
**phase-dependent**: high-volume low-intensity in preparation, pyramidal
pre-competition, polarized in the competition phase. In one 16-week trial in
well-trained runners, all approaches improved performance, but switching
pyramidal → polarized maximised the gain.

**Planner rule:** default to pyramidal in a base block and polarized closer to
an event. The commonest real-world error is not picking the wrong model — it is
letting easy days drift up into the threshold zone, which produces a
grey-zone week that is too hard to recover from and too easy to drive
adaptation. If the athlete's easy sessions keep creeping up, that is the problem
to fix before changing the model.

## 2. The order to build a week in

Do not fill days chronologically. Place by constraint priority — the most
constrained session first, so it never gets displaced by something cheaper.

```
1. Fix the immovables
   Race, event, travel, work/school blocks, mandatory rest days.

2. Place the key sessions (choose 2–3 per week, no more)
   The 1–2 sessions this block actually exists to develop, plus the long
   session. Everything else is support. Put them on the days with the best
   recovery going in — typically after a rest or easy day.

3. Place fresh-required sessions
   Anything with load.neural = high (power, intensive plyometrics, sprint work).
   These need to come BEFORE endurance in the day and BEFORE fatigue in the
   week. They are cheap in volume and expensive in freshness.

4. Place high-damage sessions
   Anything with load.damage = high (eccentric-biased gym). Schedule these
   EARLY in the microcycle and 48–72 h clear of any key endurance session.
   In a taper or race week they do not get placed at all.

5. Fill with low-interference work
   Upper body, isometrics, easy aerobic, extensive plyometrics, mobility.
   These are the shock absorbers — they let you keep training volume when the
   calendar is tight.

6. Verify, then adjust
   Run `scripts/check_week.py` on the draft (see §3). If a constraint breaks,
   downgrade the LOWER-priority session; never quietly move the key one.
```

**Spacing target:** ~48 h between hard sessions of the same type. Two hard
running days and one hard cycling day in a week is a sensible ceiling for most
athletes; three hard running days is where trouble usually starts.

## 3. Constraint checking

Every leaf declares `same_day_conflicts`, `spacing_h` and `pairs_well_with` in
frontmatter, so a candidate week can be validated **without reading any leaf
body**. Do not do this arithmetic in your head — hand the draft to
`scripts/check_week.py`, which enforces, in order:

1. **Same-day conflicts** — is this pair listed as conflicting? If yes and both
   must happen, put the priority session first, keep the other clearly
   sub-maximal, and separate by ≥6 h. (The checker downgrades a same-day
   conflict from `error` to `warning` once the gap is ≥6 h.)
2. **Spacing** — does the gap to the named session meet `spacing_h`? Spacing is
   measured session-start to session-start, not by calendar day. Tuesday 19:00 →
   Thursday 06:00 is 35 h, not "two days".
3. **Axis saturation** — sum the axis ratings across each rolling 72 h. Two
   `mechanical: high` sessions inside 72 h is the pattern that produces bone and
   tendon problems, even when each session looked reasonable alone.
4. **Day-after protection** — does the day after each key session have room to
   be genuinely easy?

When a constraint cannot be satisfied, say so explicitly in the plan rather than
silently violating it: *"This week has two hard run days 36 h apart because of
the Saturday race — the Wednesday session is deliberately shortened for that
reason."* A stated compromise is coachable; a hidden one is not. That is exactly
the distinction the checker draws between an `error` (fix it) and a `warning`
(state it and proceed).

## 4. Weekly archetypes

Starting templates, not prescriptions. Adjust to the athlete's actual
availability before proposing.

> **For this athlete (§0):** in every template below, read "key intensity" and
> "long session" as **cycling** by default — running appears only when the athlete
> asks for it. The two athlete-specific templates at the end of this section are
> the usual starting points.

**Endurance-primary, gym as support (3 endurance + 2 gym)**
```
Mon  gym/lower-max-strength (or lower-power) + easy aerobic later, ≥6 h apart
Tue  key intensity (running or cycling intervals)
Wed  easy aerobic / extensive plyo in warm-up
Thu  gym/upper-body + easy aerobic
Fri  rest or very easy
Sat  long session (key)
Sun  easy aerobic or rest
```

**Strength-primary, endurance as support**
```
Mon  lower-body strength (key)
Tue  Z2 aerobic — low interference, protects Wednesday
Wed  upper body
Thu  lower-body power or intensive plyo (fresh)
Fri  Z2 aerobic or rest
Sat  lower-body strength (key)
Sun  rest
```

**Time-crunched (4 sessions total)**
```
Tue  gym lower (strength, then easy spin if time)
Thu  key intensity session
Sat  long session
Sun  upper body or isometrics
```
When sessions are few, cut *intensity variety* before cutting frequency —
frequency is what maintains tissue tolerance.

**This athlete — default week, strength-build phase (§0), uninjured**
```
Mon  lower-body gym (rotate: max-strength / eccentric / full-body) — key strength
Tue  cycling/endurance — easy Z2 (protects Mon, low interference)
Wed  gym/upper-body (or climbing)
Thu  lower-body gym (a DIFFERENT type from Mon) or plyometrics, fresh
Fri  cycling/endurance — easy Z2
Sat  rest / optional non-training movement (not counted)
Sun  rest
```
2 rides + 2 lower gym (rotated for variety) + 1 upper, 2 rest days. Skiing is the
season goal, so the leg work is the priority and the riding is deliberately easy.
Returning-to-load caveat (§0) applies right now — hold loads conservative.

**This athlete — cycling-primary week (more riding available)**
```
Mon  lower-body gym, kept SUBMAXIMAL (supports the riding, doesn't fight it)
Tue  cycling/endurance — easy Z2
Wed  gym/upper-body (or climbing) + optional plyometrics/extensive in warm-up
Thu  cycling — longer or slightly harder ride (the week's aerobic key)
Fri  gym/strength-endurance (stairs) OR rest, athlete's choice
Sat  cycling/endurance or mountain hike if a trip is on
Sun  rest
```
When cycling steps up to 3×, lower-body gym eases to one submaximal session plus
optional strength-endurance, so total leg load stays manageable (§0).

## 5. Deload

Every 3–5 weeks, or when readiness markers trend down for ~5+ days, or after any
block that included an event.

- Cut **volume** by roughly 40–50%; **keep intensity and frequency**. Same shape
  of week, smaller sessions. Dropping frequency loses the tissue exposure that
  keeps the athlete robust.
- Remove high-`damage` work entirely for that week — this is the one axis worth
  zeroing rather than reducing.
- A deload is not a rest week. If the athlete is genuinely dug in, prescribe
  rest and say so.

## 6. Taper

The best-supported protocol, from meta-analysis:

- **Duration:** 8–14 days is optimal for cycling and running; up to 21 days can
  still work.
- **Volume:** reduce progressively by **41–60%**. This is the variable that
  drives the effect.
- **Intensity:** unchanged. Reducing it costs the taper most of its benefit.
- **Frequency:** unchanged. Groups that held frequency improved more than groups
  that cut it — so cut session *duration*, not sessions.
- A **pre-taper overload block** amplifies the effect, but only if the taper
  that follows is real.

**Do not place in a taper:** eccentric-biased gym, intensive plyometrics, any
novel exercise, any session with high `damage`. Keep short, sharp,
low-volume intensity — strides, a few threshold minutes, low-rep speed work.
Detraining becomes a real concern beyond roughly 14–21 days without stimulus.

## 7. Returning to load

After a break, illness or a layoff, the athlete's chronic base is lower than
their memory of it. Return by:

1. **Frequency first** — restore the number of sessions at reduced duration.
2. **Duration second** — rebuild the long session against its own 30-day
   ceiling (see `load-and-recovery` §3).
3. **Intensity last** — and reintroduce it as short reps with full recovery
   before any sustained threshold work.
4. **Impact and eccentric work last of all.** Bone and tendon tolerance falls
   faster than aerobic fitness and returns more slowly. The athlete will feel
   ready to run hard before their tissue is ready to absorb it — this mismatch
   is the single most common way a comeback fails.

Expect roughly the same number of weeks to rebuild as were missed, for anything
longer than two weeks off.
