from django.core.management.base import BaseCommand

from sync.models import WeatherLocation
from sync.weather import fetch_forecast


class Command(BaseCommand):
    help = 'Sync the Open-Meteo forecast for every saved weather location'

    def handle(self, *args, **options):
        for loc in WeatherLocation.objects.all():
            try:
                n = fetch_forecast(loc)
                self.stdout.write(self.style.SUCCESS(f'{loc.name}: synced {n} hourly records'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'{loc.name}: failed to fetch weather: {e}'))
