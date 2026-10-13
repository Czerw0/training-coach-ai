from django.conf import settings
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
    # nullable: log_injury only requires body_part; unknown severity is valid
    severity = models.CharField(max_length=20, choices=INJURY_CHOICES, null=True, blank=True)
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


class SyncStatus(models.Model):
    state = models.CharField(max_length=20, default="idle")  # idle | running | done | error
    message = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.pk = 1  # singleton
        super().save(*args, **kwargs)



class ApiUsage(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    model = models.CharField(max_length=60)
    input_tokens = models.IntegerField(default=0)            
    cache_creation_tokens = models.IntegerField(default=0)   
    cache_read_tokens = models.IntegerField(default=0)       
    output_tokens = models.IntegerField(default=0)
    cost_usd = models.FloatField(default=0.0)
    api_calls = models.IntegerField(default=1)               
    user_message = models.CharField(max_length=300, blank=True, default="")  
    tools_used = models.CharField(max_length=255, blank=True, default="")
    prompt_version = models.CharField(max_length=40, blank=True, default="")
    config_version = models.CharField(max_length=40, blank=True, default="baseline")
    tool_trace = models.JSONField(default=list, blank=True)
    final_text = models.CharField(max_length=2000, blank=True, default="")
    round_notes = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']
 
    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} · ${self.cost_usd:.4f} · {self.model}"

class PlannedSession(models.Model):
    date = models.DateField(db_index=True)
    activity_type = models.CharField(max_length=50)        
    title = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")
    duration_minutes = models.IntegerField(null=True, blank=True)
    intensity = models.CharField(max_length=20, blank=True, default="")   
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=10, blank=True, default="")  
 
    class Meta:
        ordering = ['date']
 
    def __str__(self):
        return f"{self.date} {self.activity_type}"


class PlannedExercise(models.Model):
    session = models.ForeignKey(PlannedSession, on_delete=models.CASCADE, related_name="exercises")
    name = models.CharField(max_length=255)
    sets = models.IntegerField(null=True, blank=True)
    reps = models.IntegerField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    notes = models.CharField(max_length=500, blank=True, default="")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.name} ({self.sets}x{self.reps}) for session {self.session_id}"

class AiInsight(models.Model):
    """One saved set of Apex insights for an activity or a Today/Stats tile.
    Served from here on revisit; regenerated only on an explicit refresh."""
    scope = models.CharField(max_length=20)          # activity / sleep / hrv / form / injuries
    key = models.CharField(max_length=40)            # activity id, or the date for tiles
    items = models.JSONField(default=list)           # [{"title": ..., "text": ...}]
    model = models.CharField(max_length=60, blank=True, default="")
    prompt_version = models.CharField(max_length=40, blank=True, default="")
    cost_usd = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["scope", "key"], name="unique_insight_scope_key")]

    def __str__(self):
        return f"{self.scope}:{self.key} · {len(self.items)} insights"


class CoachPrompt(models.Model):
    """Append-only versions of one user's coach instructions. The newest row is
    the active one; an empty `text` means "back to the default" (INSTRUCTIONS in
    coach/agent.py). Rows are never edited, so every ApiUsage prompt tag stays
    traceable to the exact text that produced it."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="coach_prompts")
    version = models.PositiveIntegerField()
    text = models.TextField(blank=True, default="")
    note = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [models.UniqueConstraint(fields=["user", "version"], name="unique_prompt_user_version")]

    def __str__(self):
        return f"{self.user} v{self.version}{'' if self.text else ' (default)'}"
