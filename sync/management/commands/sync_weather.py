from sync.models import WeatherHourly
import datetime as dt
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware



class Command(BaseCommand):
    help = 'Sync weather data from Open-Meteo API'

    def handle(self, *args, **options):
        self.stdout.write('Syncing weather...')

        data = self._fetch_weather()
        if not data:
            self.stdout.write(self.style.ERROR('Failed to fetch weather'))
            return

        hourly = data['hourly']
        count = 0

        for dt_str, temp, humidity, precip_prob, precip, cloud, wind, code, uv, is_day in zip(
            hourly['time'],
            hourly['temperature_2m'],
            hourly['relative_humidity_2m'],
            hourly['precipitation_probability'],
            hourly['precipitation'],
            hourly['cloud_cover'],
            hourly['wind_speed_10m'],
            hourly['weather_code'],
            hourly['uv_index'],
            hourly['is_day'],
        ):
            try:
                parsed_dt = dt.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M")
                aware_dt = make_aware(parsed_dt)

                WeatherHourly.objects.update_or_create(
                    datetime=aware_dt,
                    defaults={
                        'temp': temp,
                        'humidity': humidity,
                        'precipitation_probability': precip_prob,
                        'precipitation': precip,
                        'cloud_cover': cloud,
                        'wind_speed': wind,
                        'weather_code': code,
                        'uv_index': uv,
                        'is_day': bool(is_day),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error saving {dt_str}: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Synced {count} hourly records'))
        WeatherHourly.objects.filter(
            datetime__lt=timezone.now() - dt.timedelta(days=2)
        ).delete()

    def _fetch_weather(self):
        try:
            import requests
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": 52.23,
                "longitude": 21.01,
                "hourly": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "precipitation_probability",
                    "precipitation",
                    "cloud_cover",
                    "wind_speed_10m",
                    "weather_code",
                    "uv_index",
                    "is_day",
                ],
                "timezone": "Europe/Warsaw",
                "forecast_days": 7
            }
            response = requests.get(url, params=params)
            return response.json()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fetching weather: {e}"))
            return None

if __name__ == "__main__":
    command = Command()
    command.handle()