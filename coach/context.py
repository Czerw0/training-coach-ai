import datetime
from django.db.models import Sum, Q
from django.utils import timezone
from sync.models import Activity, HRVRecord, SleepRecord, DailyStats, WeatherHourly, UserProfile, FTPRecord, IndoorCyclingWorkout, Exercise
from coach.models import Injury, Goal, DailyFeeling, CoachRecommendation, PlannedSession
from coach.training_skills import list_skills


# skating instruction days, Mon=0..Sun=6 — empty while paused for July/August,
# restore the set (e.g. {0, 1, 2, 6}) when the season resumes
INSTRUCTION_DAYS = set()

# open-meteo codes: https://open-meteo.com/en/docs#api-formats
WEATHER_CODES = {
    0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    71: "light snow", 73: "snow", 75: "heavy snow",
    80: "rain showers", 81: "rain showers", 82: "heavy showers",
    95: "thunderstorm",
}


def _round(value, ndigits=1):
    """round, or None if value is None"""
    return round(value, ndigits) if value is not None else None


def _summarise_weather(hours):
    """Collapse hourly rows into one short line per day-part"""
    blocks = {}
    for h in hours:
        dt = h['datetime']
        hour = dt.hour
        day = dt.date().isoformat()
        if 6 <= hour < 12:
            block = 'morning (06-12)'
        elif 12 <= hour < 18:
            block = 'afternoon (12-18)'
        elif 18 <= hour < 22:
            block = 'evening (18-22)'
        else:
            block = 'night (22-06)'
        blocks.setdefault(day, {}).setdefault(block, []).append(h)

    summary = {}
    for day, day_blocks in blocks.items():
        summary[day] = {}
        for block, rows in day_blocks.items():
            temps = [r['temp'] for r in rows if r['temp'] is not None]
            rain_probs = [r['precipitation_probability'] for r in rows if r['precipitation_probability'] is not None]
            winds = [r['wind_speed'] for r in rows if r['wind_speed'] is not None]
            codes = [r['weather_code'] for r in rows if r['weather_code'] is not None]

            temp_str = f"{round(min(temps))}-{round(max(temps))}C" if temps else "n/a"
            rain_str = f"{max(rain_probs)}% max" if rain_probs else "n/a"
            wind_str = f"{round(min(winds))}-{round(max(winds))} km/h" if winds else "n/a"
            cond_str = WEATHER_CODES.get(max(codes), f"code {max(codes)}") if codes else "n/a"

            summary[day][block] = f"{temp_str}, rain {rain_str}, wind {wind_str}, {cond_str}"
    return summary


def _clean_activities(rows):
    """Round Garmin's long floats"""
    cleaned = []
    for a in rows:
        cleaned.append({
            'date': a['start_time'].date().isoformat() if a['start_time'] else None,
            'type': a['activity_type'],
            'duration_min': _round((a['duration_seconds'] or 0) / 60, 0),
            'distance_km': _round((a['distance_meters'] or 0) / 1000, 1) if a['distance_meters'] else None,
            'avg_hr': a['avg_hr'],
            'load': _round(a['training_load'], 0),
            'effect': a['training_effect_label'],
            'tss': _round(a['tss'], 0),
            'avg_power': a['avg_power'],
            'norm_power': a['normalized_power'],
        })
    return cleaned


def build_context():
    today = datetime.date.today()
    now = timezone.now()

    # plannable window — must stay in sync with PLANNING_WINDOW_DAYS in tools.py
    next_14_days = []
    for i in range(14):
        d = today + datetime.timedelta(days=i)
        next_14_days.append({
            'date': d.isoformat(),
            'weekday': d.strftime('%A'),
            'usual_instruction_day': d.weekday() in INSTRUCTION_DAYS,
        })

    # capped at 28 days so a long bulk plan doesn't bloat every future message
    calendar = PlannedSession.objects.filter(
        date__gte=today,
        date__lte=today + datetime.timedelta(days=28),
    ).order_by('date').values('date', 'title', 'activity_type', 'created_by', 'completed')

    profile = UserProfile.objects.first()
    profile_data = {
        'ftp_watts': profile.ftp_watts if profile else None,
        'max_hr': profile.max_hr if profile else None,
        'lthr': profile.lthr if profile else None,
        'weight_kg': profile.weight_kg if profile else None,
        'primary_sport': profile.primary_sport if profile else None,
        'injury_history': profile.injury_history if profile else None,
        'athlete_notes': profile.athlete_notes if profile else None,
    }

    recent_recommendations = list(CoachRecommendation.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values('date', 'recommendation', 'user_message'))

    load_7 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=7)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    load_28 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=28)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    # ACWR = 7-day load / (28-day load / 4)
    acute_chronic_ratio = round(load_7 / (load_28 / 4), 2) if load_28 else None

    activities_raw = list(Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=14)
    ).order_by('-start_time').values(
        'start_time', 'activity_type', 'duration_seconds', 'distance_meters',
        'avg_hr', 'training_load', 'training_effect_label', 'tss',
        'avg_power', 'normalized_power',
    ))
    activities = _clean_activities(activities_raw)

    hrv = list(HRVRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values('date', 'hrv_rmssd', 'hrv_status', 'resting_hr'))

    sleep_raw = list(SleepRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date', 'score', 'duration_hours', 'deep_sleep_hours', 'body_battery_change',
    ))
    sleep = [{
        'date': s['date'].isoformat(),
        'score': s['score'],
        'duration_h': _round(s['duration_hours'], 1),
        'deep_h': _round(s['deep_sleep_hours'], 1),
        'bb_change': s['body_battery_change'],
    } for s in sleep_raw]

    daily_stats = list(DailyStats.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date', 'body_battery_high', 'body_battery_low', 'stress_level_avg',
        'steps', 'recovery_time_hours', 'training_status', 'acwr_ratio',
    ))

    # fitness trend + resolved injuries deliberately not loaded here — big
    # and rare, not worth paying for every turn. on demand via
    # get_fitness_trend / get_resolved_injury_history (tools.py)

    ftp_history = list(FTPRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=30)
    ).order_by('-date').values('date', 'ftp_watts'))

    feelings = list(DailyFeeling.objects.filter(
        date__gte=today - datetime.timedelta(days=14)
    ).order_by('-date').values(
        'date', 'energy_level', 'muscle_soreness', 'muscle_sore', 'motivation', 'notes',
    ))

    active_injuries = list(Injury.objects.filter(
        date_started__lte=today
    ).filter(
        Q(date_resolved__isnull=True) | Q(date_resolved__gte=today)
    ).values(
        'body_part', 'severity', 'description',
        'affects_running', 'affects_cycling', 'date_started',
    ))

    active_goals = list(Goal.objects.filter(is_active=True).values(
        'title', 'goal_type', 'target_date', 'description',
    ))

    weather_hours = list(WeatherHourly.objects.filter(
        datetime__gte=now,
        datetime__lte=now + datetime.timedelta(hours=48)
    ).order_by('datetime').values(
        'datetime', 'temp', 'precipitation_probability', 'wind_speed', 'weather_code',
    ))
    weather_summary = _summarise_weather(weather_hours)

    indoor_cyc_workouts = list(IndoorCyclingWorkout.objects.all().values(
        'name', 'category', 'duration_min', 'intensity_factor', 'tss', 'description'
    ))

    # index only — progression/injury notes are the detail tier, fetched via
    # get_exercise_detail (tools.py) only when prescribing a gym session
    exercise_library = list(Exercise.objects.all().values(
        'name', 'category', 'target_muscle', 'equipment', 'description'
    ))

    last_stats = DailyStats.objects.order_by('-date').first()
    last_sync_date = last_stats.date.isoformat() if last_stats else None

    return {
        'today': f"{today.isoformat()} ({today.strftime('%A')})",
        'next_14_days': next_14_days,
        'last_garmin_data_date': last_sync_date,
        'calendar': list(calendar),
        'user_profile': profile_data,
        'training_load': {
            '7_days': round(load_7, 1),
            '28_days': round(load_28, 1),
            'acute_chronic_ratio': acute_chronic_ratio,
            'interpretation': (
                'High injury risk — consider reducing load' if acute_chronic_ratio and acute_chronic_ratio > 1.3
                else 'Optimal training zone' if acute_chronic_ratio and 0.8 <= acute_chronic_ratio <= 1.3
                else 'Undertraining — safe to increase load' if acute_chronic_ratio and acute_chronic_ratio < 0.8
                else 'Insufficient data'
            ),
        },
        'recent_activities': activities,
        'recent_recommendations': recent_recommendations,
        'recovery': {
            'hrv_last_7_days': hrv,
            'sleep_last_7_days': sleep,
            'daily_stats_last_7_days': daily_stats,
        },
        'ftp_history': ftp_history,
        'daily_feelings_last_14_days': feelings,
        'active_injuries': active_injuries,
        'active_goals': active_goals,
        'weather_next_48h': weather_summary,
        'indoor_cycling_workouts': indoor_cyc_workouts,
        'exercise_library': exercise_library,
        'training_skills': list_skills(),
    }