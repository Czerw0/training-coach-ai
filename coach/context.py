import datetime
from django.db.models import Sum, Q
from django.utils import timezone
from sync.models import Activity, HRVRecord, SleepRecord, DailyStats, WeatherHourly, UserProfile
from coach.models import Injury, Goal, DailyFeeling, CoachRecommendation
from sync.models import FTPRecord


# Minimal WMO weather code -> short label. Only the codes that actually occur
# in Warsaw forecasts. Anything unmapped falls back to "code N".
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
    """Round a float, but pass None through untouched."""
    return round(value, ndigits) if value is not None else None


def _summarise_weather(hours):
    """
    Turn a flat list of hourly rows into a compact per-day, per-block summary.

    Hourly weather is the single biggest part of the context. Sending 48-72 raw
    rows wastes tokens — the coach only needs to know "when is it dry, how warm,
    how windy" per part of the day. This collapses ~48 rows into ~9 short lines.
    """
    # Group hours into day -> block
    blocks = {}  # { 'YYYY-MM-DD': { 'morning (6-12)': [rows], ... } }

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

    # Build a one-line string per block
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
            # Use the most significant (highest) code as the representative condition
            cond_str = WEATHER_CODES.get(max(codes), f"code {max(codes)}") if codes else "n/a"

            summary[day][block] = (
                f"{temp_str}, rain {rain_str}, wind {wind_str}, {cond_str}"
            )

    return summary


def _clean_activities(rows):
    """
    Round the wasteful long floats Garmin returns (e.g. 5406.47607421875) and
    convert seconds->minutes, meters->km so the numbers are both smaller in
    tokens and easier for the model to reason about.
    """
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


# ---------------------------------------------------------------------------
# Main context builder
# ---------------------------------------------------------------------------

def build_context():
    today = datetime.date.today()
    now = timezone.now()

    # --- User Profile (static, but small and critical) ---
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

    # --- Recent coach recommendations (memory across days) ---
    recent_recommendations = list(CoachRecommendation.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values('date', 'recommendation', 'user_message'))

    # --- Training Load + acute:chronic ratio ---
    load_7 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=7)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    load_28 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=28)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    acute_chronic_ratio = round(load_7 / (load_28 / 4), 2) if load_28 else None

    # --- Recent Activities (last 14 days, trimmed + cleaned) ---
    activities_raw = list(Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=14)
    ).order_by('-start_time').values(
        'start_time',
        'activity_type',
        'duration_seconds',
        'distance_meters',
        'avg_hr',
        'training_load',
        'training_effect_label',
        'tss',
        'avg_power',
        'normalized_power',
    ))
    activities = _clean_activities(activities_raw)

    # --- HRV last 7 days ---
    hrv = list(HRVRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date', 'hrv_rmssd', 'hrv_status', 'resting_hr',
    ))

    # --- Sleep last 7 days (durations rounded) ---
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

    # --- Daily Stats last 7 days (volatile metrics only) ---
    # VO2max / endurance change slowly, so we DON'T repeat them here 7x —
    # they live in fitness_trend below instead.
    daily_stats = list(DailyStats.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date',
        'body_battery_high',
        'body_battery_low',
        'stress_level_avg',
        'steps',
        'recovery_time_hours',
        'training_status',
        'acwr_ratio',
    ))

    ftp_history = list(FTPRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=180)
    ).order_by('-date').values('date', 'ftp_watts'))
    
    # --- Fitness trend (slow-moving metrics over 90 days, sparse) ---
    # This is what lets the coach answer "how has my VO2max changed vs a month ago".
    fitness_trend = list(DailyStats.objects.filter(
        date__gte=today - datetime.timedelta(days=90),
    ).exclude(
        vo2max_cycling__isnull=True
    ).order_by('-date').values(
        'date', 'vo2max_running', 'vo2max_cycling', 'endurance_score',
    )[:15])

    # --- Daily Feelings last 14 days ---
    feelings = list(DailyFeeling.objects.filter(
        date__gte=today - datetime.timedelta(days=14)
    ).order_by('-date').values(
        'date', 'energy_level', 'muscle_soreness', 'muscle_sore', 'motivation', 'notes',
    ))

    # --- Active Injuries ---
    active_injuries = list(Injury.objects.filter(
        date_started__lte=today
    ).filter(
        Q(date_resolved__isnull=True) | Q(date_resolved__gte=today)
    ).values(
        'body_part', 'severity', 'description',
        'affects_running', 'affects_cycling', 'date_started',
    ))

    # --- Recently resolved injuries (last 6 months) ---
    recent_resolved_injuries = list(Injury.objects.filter(
        date_resolved__gte=today - datetime.timedelta(days=180),
        date_resolved__lt=today,
    ).values(
        'body_part', 'severity', 'description',
        'affects_running', 'affects_cycling',
        'date_started', 'date_resolved',
    ))

    # --- Active Goals ---
    active_goals = list(Goal.objects.filter(
        is_active=True
    ).values(
        'title', 'goal_type', 'target_date', 'description',
    ))

    # --- Weather next 48h, summarised into per-day blocks ---
    weather_hours = list(WeatherHourly.objects.filter(
        datetime__gte=now,
        datetime__lte=now + datetime.timedelta(hours=48)
    ).order_by('datetime').values(
        'datetime', 'temp', 'precipitation_probability', 'wind_speed', 'weather_code',
    ))
    weather_summary = _summarise_weather(weather_hours)

    return {
        'today': str(today),
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
        'fitness_trend': fitness_trend,
        'daily_feelings_last_14_days': feelings,
        'active_injuries': active_injuries,
        'recent_resolved_injuries': recent_resolved_injuries,
        'active_goals': active_goals,
        'ftp_history': ftp_history,
        'weather_next_48h': weather_summary,
    }