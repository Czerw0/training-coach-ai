---
name: endurance
category: cycling
description: Use when planning Z2 aerobic base rides — the lowest-interference volume in the library and the default filler around key sessions; check weather for outdoor rides.
load: {neural: low, mechanical: low, metabolic: moderate, damage: low}
residual_fatigue_h: 12
same_day_conflicts: []
spacing_h: {}
pairs_well_with: [gym/upper-body, gym/lower-isometric, gym/lower-eccentric, gym/lower-max-strength, running/intervals, plyometrics/extensive]
prerequisites: []
contraindicated_if: [systemic illness, unresolved acute injury aggravated by pedalling]
see_also: [principles/planning-the-week, cycling/intervals]
---

# Cycling — endurance

> DRAFT — coach to verify. General strength-and-conditioning guidance, not
> individualised medical advice.

> **This athlete —** cycling is the **second main sport** and the default aerobic
> engine (running is off the table unless requested, per `running/*`). A
> **direct-drive smart trainer** is available, so structured indoor Z2 is always
> an option regardless of weather — pull a matching workout with
> `get_workout_detail`; outdoor rides still get checked against `weather_next_48h`.
> **Right now (August–September, ski-strength phase) the emphasis is easy,
> consistent riding — rebuilding aerobic consistency rather than chasing big
> kilometres or FTP.** Cycling frequency flexes 1–2× per week around the athlete's
> injuries, time and other activities; when the week is cycling-primary, lower-body
> gym eases off to support it (`principles/planning-the-week`).

## Use when

Steady Zone 2 aerobic riding. This is the highest-value **structural** session
in the library: it carries large amounts of weekly load at almost no cost on the
`damage`, `mechanical` and `neural` axes, which makes it the session that lets
everything else fit.

Reach for it when the week needs volume, when the day after a hard session needs
filling, or when a hard session has been downgraded for readiness.

## Don't use when

- The athlete has systemic illness symptoms.
- It would displace a key session it's meant to support. Z2 is the filler, not
  the priority — unless the block's goal is explicitly aerobic base, in which
  case the long ride *is* the key session.

## Prescription

| Variant | Duration | Intensity | Notes |
|---|---|---|---|
| Recovery spin | 30–60 min | <55% FTP, very easy | Day after a hard session; genuinely easy |
| Standard Z2 | 60–120 min | ~55–75% FTP, Zone 2 HR | The default aerobic session |
| Long ride | 2.5–5 h | Z2 with optional short tempo blocks | The week's key aerobic stressor |
| Indoor Z | 45–90 min | prescribed by watts off current FTP | Pull `get_workout_detail` for a matching workout |

**Intensity discipline is the whole session.** Conversational — able to hold a
full sentence. If power or HR drifts up, ease off. The commonest way this
session fails is by creeping into the threshold grey zone, which turns a
recovery-friendly ride into one that costs the next day.

**Fuelling:** longer rides need carbohydrate through the ride. Short easy spins
can be done fasted if that fits the athlete's goals and they have no history of
under-fuelling. If an athlete raises concerns about energy availability, weight
loss, or persistent fatigue alongside restriction, stop planning around it and
route them to a sports dietitian or physician — that is outside what this
library handles.

## Dosing and progression

- Build **frequency first**, then duration of the long ride, then total weekly
  hours. Frequency distributes the same volume across more, smaller exposures.
- Progress the **long ride** against its own 30-day ceiling, not against last
  week's total (see `principles/load-and-recovery` §3).
- Do not progress Z2 by making it faster. Turning easy rides into tempo is the
  single most common way an aerobic block fails: too hard to recover from, too
  easy to drive an intensity adaptation.
- **Regression path:** shorten → recovery spin → rest.

## Scheduling

**Hard rules:**
- The long ride still needs an easier day after it. Don't chain it into hard
  intervals or a long run.

**Preferences:**
- Everywhere else. This is the session with no conflicts — use it to absorb the
  days around key work.
- Excellent the day after intensity as a flush, and excellent paired with any
  gym day including eccentric work, since sore legs tolerate pedalling far
  better than they tolerate impact.
- For outdoor rides, check `weather_next_48h` and place the ride in the best
  window; move indoors when conditions are poor. Wet, cold long rides cost more
  recovery than the same session indoors.

**What it costs:** metabolic only, and it clears within a day. A long ride is
the exception — treat anything over ~3 h as a key session with a real recovery
requirement.

## Interactions

- **With every gym session:** the best available pairing. Cycling's low
  mechanical strain means it doesn't compete for the tissue that lifting
  stresses.
- **With `running/*`:** substituting a Z2 ride for an easy run is the standard
  move when running volume needs capping for bone or tendon reasons, and keeps
  the aerobic stimulus at a fraction of the impact cost.
- **Same-day with gym:** if both happen, lift first and ride second where the
  aim is strength, separated by ≥6 h if the day allows.
- **When a hard session is cancelled for readiness:** this is what it becomes.

## Stop rules

- Systemic illness symptoms — no session.
- Power or HR unable to reach normal Z2 at normal RPE — treat as a readiness
  signal, shorten, and reconsider the rest of the week.
- Knee pain that appears during pedalling — stop, and check bike fit and cleat
  position before prescribing more volume.

## Worked example

> **Context:** triathlete, base phase, Monday eccentric leg session done, legs
> sore. Tuesday scheduled as sweetspot but readiness markers are down and DOMS
> is present. Outdoor: rain forecast until 15:00.

> **Prescription — Tuesday:**
> - Downgrade sweetspot → Z2 endurance, 90 min
> - Target ~60–68% FTP, HR capped at the top of Zone 2
> - Indoors, or outdoors after 15:00 per `weather_next_48h`
> - Cadence 85–95, no efforts, no segments

> **Placement rationale:** DOMS from Monday would degrade the sweetspot session
> anyway, so the prescription that was going to be compromised becomes the one
> that isn't. Z2 keeps the week's aerobic volume intact at near-zero recovery
> cost and doesn't touch the tissue that's sore.

## Evidence notes

**Supported:**
- Both polarized (~75–80% low intensity) and pyramidal distributions are
  effective for well-trained endurance athletes; low-intensity volume dominates
  in both. This session is the bulk of either model.
- Weekly-percentage progression rules have no supporting evidence base; single-
  session progression relative to the recent 30-day maximum is better founded.

**Convention:**
- The 55–75% FTP band and Zone 2 boundaries. These are standard, useful and
  model-dependent — different zone systems draw the lines differently. Anchor to
  the athlete's own tested FTP or threshold HR rather than a generic table.
