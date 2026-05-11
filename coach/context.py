import datetime
import json
from django.db.models import Sum, Q
from django.utils import timezone
from sync.models import Activity, HRVRecord, SleepRecord, DailyStats, WeatherHourly, UserProfile
from coach.models import Injury, Goal, DailyFeeling


def build_context():
    today = datetime.date.today()
    now = timezone.now()

    # User Profile
    profile = UserProfile.objects.first()
    profile_data = {
        'ftp_watts': profile.ftp_watts if profile else None,
        'max_hr': profile.max_hr if profile else None,
        'lthr': profile.lthr if profile else None,
        'weight_kg': profile.weight_kg if profile else None,
        'primary_sport': profile.primary_sport if profile else None,
    }

    # Training Load
    load_7 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=7)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    load_28 = Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=28)
    ).aggregate(Sum('training_load'))['training_load__sum'] or 0

    acute_chronic_ratio = round(load_7 / (load_28 / 4), 2) if load_28 else None

    # Recent Activities (last 14 days)
    activities = list(Activity.objects.filter(
        start_time__date__gte=today - datetime.timedelta(days=14)
    ).order_by('-start_time').values(
        'start_time',
        'activity_type',
        'activity_name',
        'duration_seconds',
        'distance_meters',
        'calories',
        'avg_hr',
        'max_hr',
        'training_load',
        'training_effect_aerobic',
        'training_effect_anaerobic',
        'training_effect_label',
        'body_battery_delta',
        # HR Zones
        'hr_zone_2_seconds',
        'hr_zone_3_seconds',
        'hr_zone_4_seconds',
        'hr_zone_5_seconds',
        # Cycling specific
        'avg_power',
        'normalized_power',
        'tss',
        'intensity_factor',
        'avg_bike_cadence',
    ))

    # HRV last 7 days
    hrv = list(HRVRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date',
        'hrv_rmssd',
        'hrv_status',
        'resting_hr',
    ))

    # Sleep last 7 days
    sleep = list(SleepRecord.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date',
        'score',
        'duration_hours',
        'deep_sleep_hours',
        'rem_sleep_hours',
        'body_battery_change',
    ))

    # Daily Stats last 7 days
    daily_stats = list(DailyStats.objects.filter(
        date__gte=today - datetime.timedelta(days=7)
    ).order_by('-date').values(
        'date',
        'body_battery_high',
        'body_battery_low',
        'stress_level_avg',
        'steps',
        'total_calories',
        'training_readiness_score',
        'recovery_time_hours',
    ))

    # Daily Feelings last 14 days
    feelings = list(DailyFeeling.objects.filter(
        date__gte=today - datetime.timedelta(days=14)
    ).order_by('-date').values(
        'date',
        'energy_level',
        'muscle_soreness',
        'muscle_sore',
        'motivation',
        'notes',
    ))

    feeling_yesterday = DailyFeeling.objects.filter(
        date=today - datetime.timedelta(days=1)
    ).values(
        'energy_level',
        'muscle_soreness',
        'muscle_sore',
        'motivation',
        'notes',
    ).first()

    # Active Injuries
    active_injuries = list(Injury.objects.filter(
        date_started__lte=today
    ).filter(
        Q(date_resolved__isnull=True) | Q(date_resolved__gte=today)
    ).values(
        'body_part',
        'severity',
        'description',
        'affects_running',
        'affects_cycling',
        'date_started',
    ))

    # Active Goals
    active_goals = list(Goal.objects.filter(
        is_active=True
    ).values(
        'title',
        'goal_type',
        'target_date',
        'description',
    ))

    # Weather next 48 hours
    weather = list(WeatherHourly.objects.filter(
        datetime__gte=now,
        datetime__lte=now + datetime.timedelta(hours=48)
    ).order_by('datetime').values(
        'datetime',
        'temp',
        'precipitation_probability',
        'precipitation',
        'weather_code',
        'wind_speed',
        'cloud_cover',
        'uv_index',
        'is_day',
    ))

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
        'recovery': {
            'hrv_last_7_days': hrv,
            'sleep_last_7_days': sleep,
            'daily_stats_last_7_days': daily_stats,
        },
        'daily_feeling': {
            'today': feelings,
            'yesterday': feeling_yesterday,
        },
        'active_injuries': active_injuries,
        'active_goals': active_goals,
        'weather_next_48h': weather,
    }