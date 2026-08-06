import datetime as dt
import json
from pydantic import ValidationError
from coach.models import DailyFeeling, Goal, Injury, PlannedExercise, PlannedSession
from coach.schemas import ClearPlannedSessionsIn, PlannedSessionIn, format_validation_error
from sync.models import DailyStats, Exercise, IndoorCyclingWorkout, UserProfile

PLANNING_WINDOW_DAYS = 14   # must match next_14_days in context.py


def validate_session_date(date_str, expected_weekday, today=None):
    """Real date, right weekday, inside the plannable window (today..today+13).

    today is injectable for tests. Returns (True, parsed_date) or
    (False, error_string) — the error goes back to the model as the tool
    result so it can self-correct.
    """
    today = today or dt.date.today()

    # malformed string is itself a model error
    try:
        parsed = dt.date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return False, (
            f"Invalid date '{date_str}'. Use YYYY-MM-DD copied from next_14_days."
        )

    # actual weekday must match what the model claimed
    actual_weekday = parsed.strftime("%A")
    if actual_weekday.lower() != (expected_weekday or "").lower():
        return False, (
            f"Date mismatch: {date_str} is a {actual_weekday}, not "
            f"{expected_weekday}. Copy the exact date for {expected_weekday} "
            f"from next_14_days and try again."
        )

    # weekday match alone isn't enough — a correct Saturday a month out,
    # calculated blind, would slip through otherwise
    window_end = today + dt.timedelta(days=PLANNING_WINDOW_DAYS - 1)
    if not (today <= parsed <= window_end):
        return False, (
            f"Date {date_str} is outside the plannable window "
            f"({today.isoformat()} to {window_end.isoformat()}). Only dates "
            f"listed in next_14_days can be scheduled."
        )

    return True, parsed


def log_daily_feeling(energy_level=None, muscle_soreness=None,
                      sore_muscles=None, motivation=None, notes=None):
    """Save or update how the athlete feels today.

    Only overwrites fields that were actually provided, so a second call the
    same day (e.g. logging soreness in the morning, alcohol in the evening)
    doesn't wipe earlier values.
    """
    today = dt.date.today()
    obj, created = DailyFeeling.objects.get_or_create(date=today)

    if energy_level is not None:
        obj.energy_level = energy_level
    if muscle_soreness is not None:
        obj.muscle_soreness = muscle_soreness
    if sore_muscles is not None:
        obj.muscle_sore = sore_muscles
    if motivation is not None:
        obj.motivation = motivation
    if notes is not None:
        # append, don't overwrite — same-day notes accumulate
        obj.notes = f"{obj.notes} | {notes}" if obj.notes else notes
    obj.save()

    action = "Created" if created else "Updated"
    return f"{action} today's feeling log."


def log_injury(body_part, severity=None, description=None,
               affects_running=None, affects_cycling=None):
    today = dt.date.today()
    # update the active injury on this body part if one exists, else create
    existing = Injury.objects.filter(
        body_part__iexact=body_part,
        date_resolved__isnull=True,
    ).first()

    if existing:
        if severity is not None:
            existing.severity = severity
        if description is not None:
            existing.description = description
        if affects_running is not None:
            existing.affects_running = affects_running
        if affects_cycling is not None:
            existing.affects_cycling = affects_cycling
        existing.save()
        return f"Updated active injury: {body_part}."

    Injury.objects.create(
        date_started=today,
        body_part=body_part,
        severity=severity,
        description=description,
        affects_running=affects_running,
        affects_cycling=affects_cycling,
    )
    return f"Logged new injury: {body_part}."


def resolve_injury(body_part):
    today = dt.date.today()
    updated = Injury.objects.filter(
        body_part__icontains=body_part,
        date_resolved__isnull=True,
    ).update(date_resolved=today)
    if updated:
        return f"Marked {body_part} injury as resolved today."
    return f"No active injury found matching '{body_part}'."


def adjust_goal(title, goal_type=None, target_date=None,
                description=None, is_active=True):
    obj, created = Goal.objects.update_or_create(
        title=title,
        defaults={
            'goal_type': goal_type,
            'target_date': target_date,
            'description': description,
            'is_active': is_active,
        }
    )
    action = "Created" if created else "Updated"
    return f"{action} goal: {title}."


def append_athlete_note(note):
    """Append a dated note to athlete_notes. Never overwrites."""
    from sync.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(pk=1)
    stamp = dt.date.today().isoformat()
    entry = f"\n[{stamp}] {note}"
    profile.athlete_notes = (profile.athlete_notes or "") + entry
    profile.save()
    return f"Appended note to athlete profile: {note}"


def create_planned_session(date, weekday, activity_type, title="",
                           description="", duration_minutes=None,
                           intensity="", exercises=None):
    """Write one planned session — after Pydantic validates the shape and
    validate_session_date validates the date. Both matter: one catches a bad
    payload, the other a claimed weekday that doesn't match the real date.
    """
    try:
        payload = PlannedSessionIn(
            date=date, weekday=weekday, activity_type=activity_type,
            title=title, description=description,
            duration_minutes=duration_minutes, intensity=intensity,
            exercises=exercises or [],
        )
    except ValidationError as exc:
        return format_validation_error(exc)   # goes back to the model, nothing written

    ok, result = validate_session_date(payload.date, payload.weekday)
    if not ok:
        return result   # goes back to the model, nothing written

    session = PlannedSession.objects.create(
        date=result, activity_type=payload.activity_type, title=payload.title,
        description=payload.description, duration_minutes=payload.duration_minutes,
        intensity=payload.intensity, created_by="ai",
    )
    if payload.exercises:
        PlannedExercise.objects.bulk_create([
            PlannedExercise(
                session=session, order=i, name=ex.name, sets=ex.sets,
                reps=ex.reps, weight_kg=ex.weight_kg, notes=ex.notes,
            )
            for i, ex in enumerate(payload.exercises)
        ])

    return f"Planned {activity_type} on {date} ({weekday})"


def clear_planned_sessions(date, weekday):
    """Remove all planned sessions on a date. Same validation as create —
    a bad date here clears the wrong day."""
    try:
        payload = ClearPlannedSessionsIn(date=date, weekday=weekday)
    except ValidationError as exc:
        return format_validation_error(exc)

    ok, result = validate_session_date(payload.date, payload.weekday)
    if not ok:
        return result

    n, _ = PlannedSession.objects.filter(date=result).delete()
    return f"Cleared {n} planned session(s) on {date} ({weekday})"

def get_workout_detail(name):
    w = IndoorCyclingWorkout.objects.filter(name__iexact=name).first()
    if not w:
        return f"No workout '{name}'."
    profile = UserProfile.objects.first()
    ftp = (profile.ftp_watts if profile and profile.ftp_watts else 250)
    return f"{w.name} at FTP {ftp}W: {w.detail_watts(ftp)}"


def get_exercise_detail(name):
    """Full detail for one exercise — index only has name/category/target."""
    ex = Exercise.objects.filter(name__iexact=name).first()
    if not ex:
        return f"No exercise '{name}'."
    return (
        f"{ex.name} ({ex.category}) — target: {ex.target_muscle or 'n/a'}, "
        f"equipment: {ex.equipment or 'n/a'}. "
        f"Default {ex.default_sets or '?'}x{ex.default_reps or '?'}. "
        f"Progression: {ex.progression_notes or 'none noted'}. "
        f"Injury notes: {ex.injury_notes or 'none'}. {ex.description}"
    )


def get_fitness_trend(days=30):
    """VO2max/endurance trend — on demand only, not worth preloading every turn."""
    today = dt.date.today()
    rows = list(DailyStats.objects.filter(
        date__gte=today - dt.timedelta(days=days),
    ).exclude(
        vo2max_cycling__isnull=True
    ).order_by('-date').values(
        'date', 'vo2max_running', 'vo2max_cycling', 'endurance_score',
    )[:15])
    if not rows:
        return "No fitness trend data available."
    return json.dumps(rows, default=str)


def get_resolved_injury_history(days=60):
    """Past (healed) injuries — active ones are already in context every turn."""
    today = dt.date.today()
    rows = list(Injury.objects.filter(
        date_resolved__gte=today - dt.timedelta(days=days),
        date_resolved__lt=today,
    ).values(
        'body_part', 'severity', 'description',
        'affects_running', 'affects_cycling', 'date_started', 'date_resolved',
    ))
    if not rows:
        return f"No resolved injuries in the last {days} days."
    return json.dumps(rows, default=str)


TOOL_DEFINITIONS = [
    {
        "name": "log_daily_feeling",
        "description": (
            "Log how the athlete feels today — energy, muscle soreness, "
            "motivation, and free-text notes. Use this whenever the athlete "
            "describes their physical or mental state today: tired, sore, "
            "unmotivated, great, etc. Also use it when they mention relevant "
            "context like poor sleep, alcohol, illness, or stress. Only fill the "
            "fields the athlete actually mentions; leave the rest empty. Safe to "
            "call multiple times per day — values merge, notes accumulate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "energy_level": {
                    "type": "integer",
                    "description": "Energy level on a 1-10 scale, if mentioned"
                },
                "muscle_soreness": {
                    "type": "integer",
                    "description": "Overall muscle soreness on a 1-10 scale, if mentioned"
                },
                "sore_muscles": {
                    "type": "string",
                    "description": "Which muscles/areas are sore, e.g. 'right knee, quads'"
                },
                "motivation": {
                    "type": "integer",
                    "description": "Motivation level on a 1-10 scale, if mentioned"
                },
                "notes": {
                    "type": "string",
                    "description": "Any other relevant context the athlete shared (sleep, alcohol, stress, social plans, etc.)"
                }
            },
            "required": []
        }
    },
    {
        "name": "log_injury",
        "description": (
            "Record a new injury or update an existing active one (matched by "
            "body part). Use this when the athlete reports pain, a strain, a "
            "flare-up, or any new physical problem. Given their significant "
            "injury history, take any mention of pain seriously and log it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "body_part": {
                    "type": "string",
                    "description": "The affected body part, e.g. 'right knee', 'left wrist'"
                },
                "severity": {
                    "type": "string",
                    "enum": ["minor", "moderate", "severe"],
                    "description": "Injury severity"
                },
                "description": {
                    "type": "string",
                    "description": "Short description of the injury and how it happened"
                },
                "affects_running": {
                    "type": "boolean",
                    "description": "Whether this injury affects running"
                },
                "affects_cycling": {
                    "type": "boolean",
                    "description": "Whether this injury affects cycling"
                }
            },
            "required": ["body_part"]
        }
    },
    {
        "name": "resolve_injury",
        "description": (
            "Mark an active injury as resolved/healed. Use this when the athlete "
            "says a previously reported injury feels completely better or fully "
            "recovered. Match by body part."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "body_part": {
                    "type": "string",
                    "description": "The body part of the injury to resolve, e.g. 'right knee'"
                }
            },
            "required": ["body_part"]
        }
    },
    {
        "name": "adjust_goal",
        "description": (
            "Create a new training goal or update an existing one (matched by "
            "title). Use this when the athlete states a goal, changes one, or sets "
            "a target date — e.g. 'I want to hit 60 VO2max by September' or 'push "
            "my race back two weeks'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short title of the goal, e.g. '60 VO2max cycling'"
                },
                "goal_type": {
                    "type": "string",
                    "enum": ["weight_loss", "muscle_gain", "endurance", "strength", "flexibility", "general_health"],
                    "description": "Category of the goal"
                },
                "target_date": {
                    "type": "string",
                    "description": "Target date in YYYY-MM-DD format, if there is one"
                },
                "description": {
                    "type": "string",
                    "description": "More detail about the goal"
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether the goal is currently active (default true)"
                }
            },
            "required": ["title"]
        }
    },
    {
        "name": "append_athlete_note",
        "description": (
            "Append a dated note to the athlete's permanent profile notes. Use for "
            "LIFE CONTEXT that should persist: work schedule changes (internship, "
            "new job), instruction schedule changes, upcoming trips, equipment "
            "changes. NOT for goals (use adjust_goal), NOT for daily states (use "
            "log_daily_feeling). Append-only — it can never delete existing notes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "note": {
                    "type": "string",
                    "description": "Concise note, e.g. 'Internship starts July 1, full-time, training limited to ~4-5h/week'"
                }
            },
            "required": ["note"]
        }
    },
    {
        "name": "create_planned_session",
        "description": (
            "Add a planned training session to the athlete's calendar on a specific "
            "date. Use when planning ahead (e.g. 'plan my week'). One session per call; "
            "call multiple times to plan several days. To change a day, call "
            "clear_planned_sessions for that date first, then create the new one. "
            "Both date and weekday must be copied exactly from next_14_days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD, copied exactly from next_14_days."},
                "weekday": {"type": "string", "description": "Weekday name for this date, exactly as in next_14_days (e.g. 'Friday'). Must match the date."},
                "activity_type": {"type": "string", "enum": ["cycling", "gym_legs", "gym_upper", "skating", "tennis", "skiing", "mountaineering", "rest", "other"]},
                "title": {"type": "string", "description": "Short name, e.g. 'VO2max intervals'"},
                "description": {"type": "string", "description": "Overall notes/comment for the whole session (not per-exercise)."},
                "duration_minutes": {"type": "integer"},
                "intensity": {"type": "string", "enum": ["easy", "moderate", "hard"]},
                "exercises": {
                    "type": "array",
                    "description": (
                        "For gym_legs/gym_upper sessions: structured exercise list. "
                        "Pick names from exercise_library and call get_exercise_detail "
                        "before prescribing. Omit for non-gym activity types."
                    ),
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Exact name from exercise_library."},
                            "sets": {"type": "integer"},
                            "reps": {"type": "integer"},
                            "weight_kg": {"type": "number"},
                            "notes": {"type": "string", "description": "Per-exercise note, e.g. 'RPE 8, last set to failure'."},
                        },
                        "required": ["name"],
                    },
                },
            },
            "required": ["date", "weekday", "activity_type"],
        },
    },
    {
        "name": "clear_planned_sessions",
        "description": (
            "Delete all planned sessions on a date. Use before re-planning a day, "
            "or to remove a planned session the athlete cancelled. Both date and "
            "weekday must be copied exactly from next_14_days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "ISO date YYYY-MM-DD, copied exactly from next_14_days."},
                "weekday": {"type": "string", "description": "Weekday name for this date, exactly as in next_14_days (e.g. 'Friday'). Must match the date."},
            },
            "required": ["date", "weekday"],
        },
    },
    {
        "name": "get_workout_detail",
        "description": "Get the interval watt targets for one indoor cycling workout. Call before prescribing an indoor session. Use the exact name from indoor_workouts.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_exercise_detail",
        "description": (
            "Get progression and injury notes for one gym exercise. Call this "
            "before prescribing it, especially if the athlete has an active "
            "injury that might be relevant. Use the exact name from exercise_library."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "get_fitness_trend",
        "description": (
            "Slow-moving VO2max/endurance trend over recent weeks. Call this "
            "only when the athlete asks about long-term fitness progression — "
            "not needed for day-to-day planning."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Lookback window in days, default 30."}},
            "required": [],
        },
    },
    {
        "name": "get_resolved_injury_history",
        "description": (
            "Past (healed) injuries. Call this only when discussing recurring "
            "or historical injuries — currently active injuries are already "
            "in context every turn, so this is only for the resolved ones."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "description": "Lookback window in days, default 60."}},
            "required": [],
        },
    },
]


TOOL_FUNCTIONS = {
    "log_daily_feeling": log_daily_feeling,
    "log_injury": log_injury,
    "resolve_injury": resolve_injury,
    "adjust_goal": adjust_goal,
    "append_athlete_note": append_athlete_note,
    "create_planned_session": create_planned_session,
    "clear_planned_sessions": clear_planned_sessions,
    "get_workout_detail": get_workout_detail,
    "get_exercise_detail": get_exercise_detail,
    "get_fitness_trend": get_fitness_trend,
    "get_resolved_injury_history": get_resolved_injury_history,
}


def execute_tool(tool_name, tool_input):
    """Run a tool by name with the given arguments."""
    func = TOOL_FUNCTIONS.get(tool_name)
    if not func:
        return f"Unknown tool: {tool_name}"
    try:
        return func(**tool_input)
    except Exception as e:
        return f"Error running {tool_name}: {e}"