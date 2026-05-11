from django.db import models

class Injury(models.Model):
    INJURY_CHOICES = [
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]

    date_started = models.DateField()
    date_resolved = models.DateField(null=True, blank=True)
    body_part = models.CharField(max_length=100)
    severity = models.CharField(max_length=20, choices=INJURY_CHOICES)
    description = models.CharField(max_length=250, null=True, blank=True)
    affects_running = models.BooleanField(null=True, blank=True, default=True)
    affects_cycling = models.BooleanField(null=True, blank=True, default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_started']
    
    def __str__(self):
        return f"{self.body_part} injury starting {self.date_started} ({self.severity})"

class Goal(models.Model):
    GOAL_CHOICES = [
        ('weight_loss', 'Weight Loss'),
        ('muscle_gain', 'Muscle Gain'),
        ('endurance', 'Endurance'),
        ('strength', 'Strength'),
        ('flexibility', 'Flexibility'),
        ('general_health', 'General Health'),
    ]
    title = models.CharField(max_length=50)
    goal_type = models.CharField(max_length=20, choices=GOAL_CHOICES)
    target_date = models.DateField(null=True, blank=True)
    description = models.CharField(max_length=300, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.get_goal_type_display()})"

class DailyFeeling(models.Model):
    MUSCLE_SORE_CHOICES = [
        ('hamstrongs', 'Hamstrings'),
        ('quads', 'Quads'),
        ('calves', 'Calves'),
        ('glutes', 'Glutes'),
        ('lower_back', 'Lower Back'),
        ('upper_back', 'Upper Back'),
        ('shoulders', 'Shoulders'),
        ('arms', 'Arms'),
        ('core', 'Core'),
    ]

    date = models.DateField(unique=True)
    energy_level = models.IntegerField(null=True, blank=True) # 1-10 scale
    muscle_soreness = models.IntegerField(null=True, blank=True) # 1-10 scale
    muscle_sore = models.CharField(max_length=100, null=True, blank=True, choices=MUSCLE_SORE_CHOICES)
    motivation = models.IntegerField(null=True, blank=True) # 1-10 scale
    notes = models.CharField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Feeling on {self.date}: Energy {self.energy_level}, Soreness {self.muscele_soreness}, Motivation {self.motivation}"
