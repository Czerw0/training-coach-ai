from django.db import models
import datetime

class Injury(models.Model):
    INJURY_CHOICES = [
        ('minor', 'Minor'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ]

    date_started = models.DateField()
    date_resolved = models.DateField(null=True, blank=True)
    body_part = models.CharField(max_length=100, null=True, blank=True)
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
    goal_type = models.CharField(max_length=20, choices=GOAL_CHOICES, null=True, blank=True)
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
    notes = models.CharField(max_length=1200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Feeling on {self.date}: Energy {self.energy_level}, Soreness {self.muscle_soreness}, Motivation {self.motivation}"

class CoachRecommendation(models.Model):
    date = models.DateField(default=datetime.date.today)
    recommendation = models.TextField()
    user_message = models.TextField(null=True, blank=True)
    user_followed = models.BooleanField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Recommendation {self.date}"


class Message(models.Model):
    role = models.CharField(max_length=20)   # 'user' or 'coach'
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']