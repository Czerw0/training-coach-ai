from django.contrib import admin
from .models import Injury, Goal, DailyFeeling

admin.site.register(Injury)
admin.site.register(Goal)
admin.site.register(DailyFeeling)