from django.db import models

class Activity(models.Model):
    # identification
    garmin_id = models.CharField(max_length=64, unique=True, db_index=True)
    activity_name = models.CharField(max_length=255, null=True, blank=True)
    activity_type = models.CharField(max_length=50, db_index=True) # e.g. running, cycling, strength_training
    start_time = models.DateTimeField(db_index=True, null=True, blank=True) # maps to startTimeLocal
    location_name = models.CharField(max_length=255, null=True, blank=True)
    device_id = models.CharField(max_length=64, null=True, blank=True)

    # primary metrics
    duration_seconds = models.FloatField()
    moving_duration_seconds = models.FloatField(null=True, blank=True)
    elapsed_duration_seconds = models.FloatField(null=True, blank=True)
    distance_meters = models.FloatField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    bmr_calories = models.IntegerField(null=True, blank=True)

    # heart rate & intensity
    avg_hr = models.IntegerField(null=True, blank=True)
    max_hr = models.IntegerField(null=True, blank=True)
    # HR time in zones, seconds
    hr_zone_1_seconds = models.FloatField(null=True, blank=True)
    hr_zone_2_seconds = models.FloatField(null=True, blank=True)
    hr_zone_3_seconds = models.FloatField(null=True, blank=True)
    hr_zone_4_seconds = models.FloatField(null=True, blank=True)
    hr_zone_5_seconds = models.FloatField(null=True, blank=True)

    # training analysis
    training_load = models.FloatField(null=True, blank=True)
    training_effect_aerobic = models.FloatField(null=True, blank=True)
    training_effect_anaerobic = models.FloatField(null=True, blank=True)
    training_effect_label = models.CharField(max_length=100, null=True, blank=True) # e.g. "Base", "VO2 Max"
    vo2_max = models.FloatField(null=True, blank=True)

    # running-specific (HRM-Pro / advanced dynamics)
    avg_running_cadence = models.IntegerField("Steps per Minute", null=True, blank=True)
    max_running_cadence = models.IntegerField(null=True, blank=True)
    avg_stride_length_cm = models.FloatField(null=True, blank=True)
    avg_vertical_oscillation_cm = models.FloatField(null=True, blank=True)
    avg_vertical_ratio = models.FloatField(null=True, blank=True)
    avg_ground_contact_time_ms = models.FloatField(null=True, blank=True)
    avg_ground_contact_balance_left = models.FloatField("Left % Balance", null=True, blank=True)
    avg_running_power = models.FloatField("Watts", null=True, blank=True)
    avg_grade_adjusted_speed = models.FloatField(null=True, blank=True)

    # cycling-specific (Edge 840 + power meter)
    avg_power = models.IntegerField(null=True, blank=True)
    max_power = models.IntegerField(null=True, blank=True)
    normalized_power = models.IntegerField(null=True, blank=True)
    tss = models.FloatField("Training Stress Score", null=True, blank=True)
    intensity_factor = models.FloatField(null=True, blank=True)
    avg_bike_cadence = models.IntegerField("RPM", null=True, blank=True)
    max_bike_cadence = models.IntegerField(null=True, blank=True)

    # power time in zones, seconds
    power_zone_1_seconds = models.FloatField(null=True, blank=True)
    power_zone_2_seconds = models.FloatField(null=True, blank=True)
    power_zone_3_seconds = models.FloatField(null=True, blank=True)
    power_zone_4_seconds = models.FloatField(null=True, blank=True)
    power_zone_5_seconds = models.FloatField(null=True, blank=True)
    power_zone_6_seconds = models.FloatField(null=True, blank=True)

    # swimming-specific
    avg_swolf = models.IntegerField(null=True, blank=True)
    total_strokes = models.IntegerField(null=True, blank=True)
    avg_stroke_rate = models.FloatField(null=True, blank=True)
    lap_count = models.IntegerField(null=True, blank=True)

    # strength training
    total_sets = models.IntegerField(null=True, blank=True)
    active_sets = models.IntegerField(null=True, blank=True)
    total_reps = models.IntegerField(null=True, blank=True)
    # per-exercise detail would need a separate model linked to Activity

    # environment & health
    elevation_gain_m = models.FloatField(null=True, blank=True)
    elevation_loss_m = models.FloatField(null=True, blank=True)
    max_temp = models.FloatField(null=True, blank=True)
    min_temp = models.FloatField(null=True, blank=True)
    body_battery_delta = models.IntegerField(null=True, blank=True) # differenceBodyBattery

    # AI-coach insight email (notify_new_workouts command)
    # notified_at: null = this activity hasn't been emailed yet (the pickup
    # filter); stamped only on a successful send so failures retry next run.
    # coach_insight: the agent's own words about this workout, fed back into
    # context (coach/context.py) so it sees what it already told me.
    notified_at = models.DateTimeField(null=True, blank=True, db_index=True)
    coach_insight = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['garmin_id']),
            models.Index(fields=['start_time']),
            models.Index(fields=['activity_type']),
        ]

    def __str__(self):
        return f"{self.activity_type} - {self.start_time.date()} ({self.activity_name or 'No Name'})"

class SleepRecord(models.Model):
    date = models.DateField(unique=True)
    duration_hours = models.FloatField(null=True, blank=True)
    score = models.IntegerField(null=True, blank=True)
    deep_sleep_hours = models.FloatField(null=True, blank=True)
    rem_sleep_hours = models.FloatField(null=True, blank=True)
    light_sleep_hours = models.FloatField(null=True, blank=True)
    awake_hours = models.FloatField(null=True, blank=True)
    body_battery_change = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

class HRVRecord(models.Model):
    HRV_STATUS_CHOICES = [
        ('balanced', 'Balanced'),
        ('low', 'Low'),
        ('poor', 'Poor'),
        ('unbalanced', 'Unbalanced'),
    ]
    date = models.DateField(unique=True)
    hrv_rmssd = models.FloatField(null=True, blank=True)
    hrv_status = models.CharField(
        max_length=20,
        choices=HRV_STATUS_CHOICES,
        null=True,
        blank=True
    )
    resting_hr = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DailyStats(models.Model):
    date = models.DateField(unique=True)
    body_battery_high = models.IntegerField(null=True, blank=True)
    body_battery_low = models.IntegerField(null=True, blank=True)
    stress_level_avg = models.IntegerField(null=True, blank=True)
    recovery_time_hours = models.IntegerField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)
    total_calories = models.IntegerField(null=True, blank=True)
    vo2max_running = models.FloatField(null=True, blank=True)
    vo2max_cycling = models.FloatField(null=True, blank=True)
    training_status = models.IntegerField(null=True, blank=True)   # Garmin numeric status
    acwr_ratio = models.FloatField(null=True, blank=True)          # acute:chronic from Garmin
    endurance_score = models.IntegerField(null=True, blank=True)
    fitness_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily Stats'

class UserProfile(models.Model):
    ftp_watts = models.IntegerField(null=True, blank=True)
    max_hr = models.IntegerField(null=True, blank=True)
    lthr = models.IntegerField("Lactate Threshold HR", null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    primary_sport = models.CharField(max_length=50, default='running')
    injury_history = models.TextField(null=True, blank=True) # Could be JSON or structured text for better parsing
    athlete_notes = models.TextField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class WeatherHourly(models.Model):
    datetime = models.DateTimeField(unique=True)
    temp = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    wind_speed = models.FloatField(null=True, blank=True)
    precipitation_probability = models.IntegerField(null=True, blank=True)
    precipitation = models.FloatField(null=True, blank=True) # rain
    cloud_cover = models.IntegerField(null=True, blank=True)
    weather_code = models.IntegerField(null=True, blank=True)
    uv_index = models.FloatField(null=True, blank=True)
    is_day = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['datetime']

    def __str__(self):
        return f"{self.datetime}: {self.temp}°C"

class FTPRecord(models.Model):
    date = models.DateField(unique=True)
    ftp_watts = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"FTP {self.ftp_watts}W on {self.date}"

class IndoorCyclingWorkout(models.Model):
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=50)          # endurance, threshold, vo2max, recovery, ...
    duration_min = models.IntegerField()
    intensity_factor = models.FloatField()
    tss = models.FloatField()
    description = models.TextField(blank=True, default="")
    structure = models.JSONField(default=list, blank=True)   # [{"sec","ftp_low","ftp_high","cadence"}]
 
    class Meta:
        ordering = ["tss"]
 
    def __str__(self):
        return f"{self.name} ({self.category}, {self.duration_min}min), IF: {self.intensity_factor}, TSS: {self.tss}"

class Exercise(models.Model):
    CATEGORY_CHOICES = [
        ('legs', 'Legs'),
        ('upper', 'Upper Body'),
        ('core', 'Core'),
        ('posterior_chain', 'Posterior Chain'),
        ('mobility', 'Mobility'),
    ]
    name = models.CharField(max_length=255, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    target_muscle = models.CharField(max_length=100, blank=True, default="")
    equipment = models.CharField(max_length=100, blank=True, default="")
    default_sets = models.IntegerField(null=True, blank=True)
    default_reps = models.IntegerField(null=True, blank=True)
    progression_notes = models.TextField(blank=True, default="")
    injury_notes = models.TextField(blank=True, default="")
    description = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.category})"
 
    def detail_watts(self, ftp):
        out = []
        for s in self.structure:
            lo = round(ftp * s["ftp_low"] / 100) 
            hi = round(ftp * s["ftp_high"] / 100)
            mins = s["sec"] // 60 or s["sec"]
            unit = "m" if s["sec"] >= 60 else "s"
            watts = f"{lo}W" if lo == hi else f"{lo}-{hi}W"
            out.append(f"{mins}{unit} @ {watts}")
        return " | ".join(out)
 