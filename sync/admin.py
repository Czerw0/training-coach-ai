from django.contrib import admin
from .models import Activity, SleepRecord, HRVRecord, DailyStats, UserProfile, WeatherHourly

admin.site.register(Activity)
admin.site.register(SleepRecord)
admin.site.register(HRVRecord)
admin.site.register(DailyStats)
admin.site.register(UserProfile)
admin.site.register(WeatherHourly)