import datetime as dt
from django.core.management import call_command
from coach.models import DailyFeeling, Goal, Injury


# ---------------------------------------------------------------------------
# Tool functions — plain Python, write to the database
# ---------------------------------------------------------------------------

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
        # Append rather than overwrite, so multiple notes in a day accumulate
        obj.notes = f"{obj.notes} | {notes}" if obj.notes else notes
    obj.save()

    action = "Created" if created else "Updated"
    return f"{action} today's feeling log."


def log_injury(body_part, severity=None, description=None,
               affects_running=None, affects_cycling=None):
    today = dt.date.today()
    # Update an existing ACTIVE injury on this body part, or create a new one
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


def sync_all_data():
    """Pull the latest Garmin and weather data on demand. Slow (~60s)."""
    try:
        call_command('sync_garmin', days=1)
        call_command('sync_weather')
        return "Synced latest Garmin and weather data successfully."
    except Exception as e:
        return f"Error syncing data: {e}"
    

def append_athlete_note(note):
    """Append a dated note to athlete_notes. Never overwrites."""
    from sync.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(pk=1)
    stamp = dt.date.today().isoformat()
    entry = f"\n[{stamp}] {note}"
    profile.athlete_notes = (profile.athlete_notes or "") + entry
    profile.save()
    return f"Appended note to athlete profile: {note}"




# ---------------------------------------------------------------------------
# Tool definitions — how the LLM sees the tools
# ---------------------------------------------------------------------------

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
        "name": "sync_all_data",
        "description": (
            "Fetch the latest Garmin and weather data. This is SLOW (up to a "
            "minute) and should be used sparingly. Only call this when the athlete "
            "explicitly asks to refresh/update data (words like 'refresh', "
            "'update', 'sync', 'latest data'), or says they just completed an "
            "activity that isn't showing in the current context yet. Do NOT call "
            "it for normal questions — the context already contains recent data. "
            "Also check last_garmin_data_date in the context: if it is more than "
            "1 day old, suggest a sync before making recommendations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
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
}
]


TOOL_FUNCTIONS = {
    "log_daily_feeling": log_daily_feeling,
    "log_injury": log_injury,
    "resolve_injury": resolve_injury,
    "adjust_goal": adjust_goal,
    "sync_all_data": sync_all_data,
    "append_athlete_note": append_athlete_note,
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