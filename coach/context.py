import datetime
from django.db.models import Sum, Q
from django.utils import timezone
from sync.models import Activity, HRVRecord, SleepRecord, DailyStats, WeatherHourly, UserProfile, FTPRecord
from coach.models import Injury, Goal, DailyFeeling, CoachRecommendation, PlannedSession


# Days of the week with skating instruction: Mon=0, Tue=1, Wed=2, Sun=6.
# NOTE: if the schedule changes (e.g. July/August pause), update this set.
INSTRUCTION_DAYS = {0, 1, 2, 6}

# Minimal WMO weather code -> short label.
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
    return round(value, ndigits) if value is not None else None


def _summarise_weather(hours):
    """Collapse hourly rows into one short line per day-part. Big token saver."""
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
    """Round Garmin's long floats; seconds->min, meters->km."""
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

    # --- Precomputed calendar: the model READS weekdays, never calculates ---
    next_7_days = []
    for i in range(7):
        d = today + datetime.timedelta(days=i)
        next_7_days.append({
            'date': d.isoformat(),
            'weekday': d.strftime('%A'),
            'usual_instruction_day': d.weekday() in INSTRUCTION_DAYS,
        })

    calendar = PlannedSession.objects.filter(date__gte=today).order_by('date').values('date', 'title', 'activity_type')
    
    # --- User Profile ---
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

    # --- Cross-day memory ---
    recent_recommendations = list(CoachRecommendation.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values('date', 'recommendation', 'user_message'))

    # --- Training load + ACWR ---
    load_7 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=7)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    load_28 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=28)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    acute_chronic_ratio = round(load_7 / (load_28 / 4), 2) if load_28 else None

    # --- Recent activities (14 days, trimmed + cleaned) ---
    activities_raw = list(Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=14)
    ).order_by('-start_time').values(
        'start_time', 'activity_type', 'duration_seconds', 'distance_meters',
        'avg_hr', 'training_load', 'training_effect_label', 'tss',
        'avg_power', 'normalized_power',
    ))
    activities = _clean_activities(activities_raw)

    # --- Recovery: HRV / sleep / daily stats, 7 days ---
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

    # --- Slow-moving fitness metrics (30 days, sparse) ---
    fitness_trend = list(DailyStats.objects.filter(
        date__gte=today - datetime.timedelta(days=30),
    ).exclude(
        vo2max_cycling__isnull=True
    ).order_by('-date').values(
        'date', 'vo2max_running', 'vo2max_cycling', 'endurance_score',
    )[:15])

    ftp_history = list(FTPRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=30)
    ).order_by('-date').values('date', 'ftp_watts'))

    # --- Feelings, injuries, goals ---
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

    recent_resolved_injuries = list(Injury.objects.filter(
        date_resolved__gte=today - datetime.timedelta(days=60),
        date_resolved__lt=today,
    ).values(
        'body_part', 'severity', 'description',
        'affects_running', 'affects_cycling', 'date_started', 'date_resolved',
    ))

    active_goals = list(Goal.objects.filter(is_active=True).values(
        'title', 'goal_type', 'target_date', 'description',
    ))

    # --- Weather, summarised ---
    weather_hours = list(WeatherHourly.objects.filter(
        datetime__gte=now,
        datetime__lte=now + datetime.timedelta(hours=48)
    ).order_by('datetime').values(
        'datetime', 'temp', 'precipitation_probability', 'wind_speed', 'weather_code',
    ))
    weather_summary = _summarise_weather(weather_hours)

    # --- Data freshness: when did Garmin data last land? ---
    last_stats = DailyStats.objects.order_by('-date').first()
    last_sync_date = last_stats.date.isoformat() if last_stats else None

    return {
        'today': f"{today.isoformat()} ({today.strftime('%A')})",
        'next_7_days': next_7_days,
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
        'fitness_trend': fitness_trend,
        'ftp_history': ftp_history,
        'daily_feelings_last_14_days': feelings,
        'active_injuries': active_injuries,
        'recent_resolved_injuries': recent_resolved_injuries,
        'active_goals': active_goals,
        'weather_next_48h': weather_summary,
    }