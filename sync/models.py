from django.db import models


class Activity(models.Model):
    garmin_id = models.CharField(max_length=64, unique=True)
    date = models.DateField()
    activity_type = models.CharField(max_length=50)
    duration_minutes = models.FloatField()
    distance_km = models.FloatField(null=True, blank=True)
    avg_hr = models.IntegerField(null=True, blank=True)
    max_hr = models.IntegerField(null=True, blank=True)
    calories = models.IntegerField(null=True, blank=True)
    training_load = models.FloatField(null=True, blank=True)
    training_effect_aerobic = models.FloatField(null=True, blank=True)
    training_effect_anaerobic = models.FloatField(null=True, blank=True)
    # Running specific (HRM Pro)
    avg_cadence = models.IntegerField(null=True, blank=True)
    avg_stride_length = models.FloatField(null=True, blank=True)
    ground_contact_time = models.FloatField(null=True, blank=True)
    vertical_oscillation = models.FloatField(null=True, blank=True)
    avg_running_power = models.FloatField(null=True, blank=True)
    # Cycling specific (Edge 840 + power meter)
    avg_power = models.IntegerField(null=True, blank=True)
    normalized_power = models.IntegerField(null=True, blank=True)
    tss = models.FloatField(null=True, blank=True)
    intensity_factor = models.FloatField(null=True, blank=True)
    # Both
    avg_pace_min_per_km = models.FloatField(null=True, blank=True)
    elevation_gain_m = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.activity_type} on {self.date}"


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

    def __str__(self):
        return f"Sleep on {self.date} — score: {self.score}"


class HRVRecord(models.Model):
    HRV_STATUS_CHOICES = [
        ('balanced', 'Balanced'),
        ('low', 'Low'),
        ('poor', 'Poor'),
        ('unbalanced', 'Unbalanced'),
    ]

    date = models.DateField(unique=True)
    hrv_rmssd = models.FloatField(null=True, blank=True)
    hrv_status = models.CharField(max_length=20, choices=HRV_STATUS_CHOICES, null=True, blank=True)
    resting_hr = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"HRV on {self.date} — {self.hrv_status}"


class DailyStats(models.Model):
    TRAINING_STATUS_CHOICES = [
        ('peaking', 'Peaking'),
        ('productive', 'Productive'),
        ('maintaining', 'Maintaining'),
        ('recovery', 'Recovery'),
        ('unproductive', 'Unproductive'),
        ('overreaching', 'Overreaching'),
        ('detraining', 'Detraining'),
    ]

    date = models.DateField(unique=True)
    # Energy & stress
    body_battery_high = models.IntegerField(null=True, blank=True)
    body_battery_low = models.IntegerField(null=True, blank=True)
    stress_level_avg = models.IntegerField(null=True, blank=True)
    # Training readiness (FR955)
    training_readiness_score = models.IntegerField(null=True, blank=True)
    training_readiness_label = models.CharField(max_length=50, null=True, blank=True)
    training_status = models.CharField(max_length=20, choices=TRAINING_STATUS_CHOICES, null=True, blank=True)
    recovery_time_hours = models.IntegerField(null=True, blank=True)
    vo2max = models.FloatField(null=True, blank=True)
    endurance_score = models.FloatField(null=True, blank=True)
    # Daily totals
    total_calories_burned = models.IntegerField(null=True, blank=True)
    active_calories = models.IntegerField(null=True, blank=True)
    steps = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Daily Stats'

    def __str__(self):
        return f"Stats on {self.date} — readiness: {self.training_readiness_score}"


class UserProfile(models.Model):
    ftp_watts = models.IntegerField(null=True, blank=True)
    max_hr = models.IntegerField(null=True, blank=True)
    lthr = models.IntegerField(null=True, blank=True)
    primary_sport = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"UserProfile — FTP: {self.ftp_watts}W, MaxHR: {self.max_hr}"