---
name: load-and-recovery
kind: principles
description: How fatigue accumulates, how long it lasts, and how sessions interfere. Read once per planning turn before prescribing anything.
---

# Principles — load, fatigue and recovery

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

This file holds the reasoning that every session type shares. Leaf skills state
their own numbers and defer here for the *why*. Read it once per planning turn;
do not re-derive these rules inside a leaf file.

## 1. Fatigue is not one number

A single "load" score cannot answer "can these two sessions sit next to each
other?", because two sessions with identical training load can leave completely
different residue. Track four axes instead. Every leaf declares its own rating
on each in frontmatter (`load:`), so conflicts can be checked before any file is
read — and `scripts/check_week.py` reads exactly those ratings.

| Axis | What it is | Typical residue | What it degrades next |
|---|---|---|---|
| `neural` | CNS / motor-unit recruitment cost | 24–48 h | max speed, jump height, bar velocity, technique |
| `mechanical` | impact and tissue strain (bone, tendon, fascia) | 48–72 h | tendon/bone tolerance — the slowest tissue to adapt |
| `metabolic` | glycogen depletion, cardiovascular strain | 12–36 h | ability to hold intensity, not to produce force |
| `damage` | muscle damage / DOMS | peaks 24–72 h | running and cycling economy, force at speed |

The scheduling question is never "was yesterday hard?" but **"which axis did
yesterday load, and does today need that axis fresh?"** A hard threshold ride
and a heavy eccentric leg day both score "hard", but the ride costs almost
nothing on `damage` while the eccentric day costs almost everything.

**Practical consequence:** a high-`metabolic`, low-`damage` session (Z2 riding)
can be stacked far more densely than its perceived effort suggests. A
low-`metabolic`, high-`neural` session (jumps, sprints) feels easy and still
needs 48 h of clearance.

## 2. Interference: smaller and more specific than commonly stated

The old advice — keep gym away from endurance or you will blunt both — is too
broad. Current evidence:

- For **strength and hypertrophy**, the interference effect does not appear in
  any generalisable sense. Endurance frequency, training status and session
  timing all failed to modify the effect in the most recent large meta-analysis.
- It **is** real and worth planning around for **power and explosive strength**.
- In trained athletes, interference was stronger when strength and endurance ran
  **in the same session** than with a **6- or 24-hour gap** between them.
- Intra-session order: **resistance before endurance** favours lower-body
  dynamic strength over a programme of ≥5 weeks. No order effect was found for
  hypertrophy, static strength or aerobic capacity.

**Rules for the planner:**

1. Protect explosive/power qualities first — those are what interference
   actually threatens. Strength and hypertrophy sessions schedule far more
   freely than the traditional advice suggests.
2. If both must land on one day, separate by **≥6 h** where the athlete's day
   allows it. Same-session is the worst case, not merely a compromise.
3. In one session, run **resistance first, then endurance** — unless the
   endurance session is the week's key session, in which case priority wins and
   the gym work is kept light.
4. Running interferes with lower-body strength more than cycling does. Weight
   the constraint accordingly when the endurance mode is running.

## 3. Load progression

**Do not use a fixed weekly percentage as a safety rule.** The 10%-per-week rule
has essentially no supporting evidence: in a cohort of novice runners the
*uninjured* group averaged ~22% weekly increases, roughly double the rule, while
injuries clustered above ~30%. A 5,200-runner study found week-to-week volume
change predicted injury no better than chance.

What that study did find, and what should drive progression instead:

- **The single-session spike is the signal.** Risk rises sharply once a session
  exceeds ~10% of the longest single session in the previous 30 days. Progress
  the *long session* against its own 30-day ceiling, not the weekly total
  against last week's.
- Progressions under 10% are not automatically safe either — the same analysis
  put a 1–10% progression at a non-significant ~19% increased rate. There is
  irreducible risk; the goal is proportion, not a guarantee.
- Grow **frequency first**, then session duration, then intensity. Frequency
  distributes the same volume across more, smaller exposures.
- Progress **one variable at a time**. If duration, intensity and terrain all
  move in the same week, a bad outcome teaches nothing.

### On ACWR

Treat the acute:chronic workload ratio as a **descriptive flag, never a
predictor or a gate**. The evidence base has moved: early findings were
associations rather than causal, randomised chronic loads perform about as well
as real ones, and the ratio is confounded by missing data, returns from injury,
and planned tapers — a taper mechanically produces a "dangerous" ratio while
being the correct thing to do. If it is reported at all, it is one input among
several and never the sole decision-maker.

**Do not write ACWR into session rationale.** Say what the session actually
costs and what it needs around it.

## 4. Autoregulation and readiness

Guiding training by daily readiness is defensible but modest. HRV-guided
training beats predefined training on submaximal physiological markers with a
medium effect, but the effect on performance and VO2peak is small and not
statistically significant. Its real advantage is **fewer non-responders and more
positive responders** — it is a variance-reduction tool, not a performance
multiplier. Note that most HRV-guided arms ended up doing *fewer* moderate and
high-intensity sessions.

So: use readiness to decide **whether today's hard session goes ahead**, not to
design the plan.

**Downgrade ladder.** When readiness signals (HRV, sleep, resting HR, subjective
wellness, residual soreness) are poor, step *down* one rung rather than skipping:

```
intensive plyo / power  →  isometric or extensive plyo
running intervals       →  tempo  →  easy run  →  rest
cycling intervals       →  sweetspot  →  Z2 endurance
heavy lower-body        →  moderate-load technique work  →  upper body
```

Subjective wellness (sleep, soreness, mood, stress) tracks acute load at least
as usefully as any device metric and costs nothing. Prefer it when device data
is absent — do not refuse to plan because a metric is missing.

Two failure modes to avoid: never let a single low overnight number cancel a
well-placed key session (compare against a rolling 7-day baseline, not
yesterday), and never let good numbers justify adding intensity that was not in
the plan.

## 5. Soreness, pain and stop rules

- **DOMS** peaks 24–72 h after unaccustomed or eccentric-biased work and
  degrades economy and force production in that window. It is a scheduling
  constraint, not a quality marker.
- **Tendon pain** during loading is acceptable up to roughly 3/10 and must not
  be worse the next morning. Rising 24-hour response = the dose was too high,
  regardless of how it felt at the time.
- **Sharp, localised or new pain** ends the session. It does not get worked
  through, and it does not get a modified session prescribed around it in the
  same turn.
- **Route to a clinician**, and do not prescribe around it: pain that wakes the
  athlete at night, swelling, giving way, loss of range, any bone-stress
  suspicion (focal tenderness on a bone, pain that worsens through a run rather
  than warming up), or any red flag the athlete raises about eating, energy
  availability, menstrual disruption or unexplained performance decline. These
  are outside what this library can plan for.
- **Illness:** systemic symptoms (fever, aches, chest involvement) mean no
  training. Return with easy aerobic work and rebuild intensity over several
  days, not in one session.

## 6. Where the numbers in this library come from

Every leaf file separates two kinds of claim in its `Evidence notes` section:

- **Supported** — from meta-analyses or controlled trials, worth stating to the
  athlete as a reason.
- **Convention** — coaching practice that is sensible and widely used but
  thinly evidenced (most specific spacing hours fall here). Present these as
  defaults, not facts.

Do not blur the two when explaining a plan. A coach reviewing this draft needs
to know which numbers they are being asked to trust.
