import os
import datetime
import time
from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from garminconnect import Garmin
from dotenv import load_dotenv
from sync.models import Activity, SleepRecord, HRVRecord, DailyStats

load_dotenv()

class Command(BaseCommand):
    help = 'Sync Garmin data to database with sport-specific mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=4,
            help='Number of past days to sync (default: 4)'
        )

    def handle(self, *args, **options):
        days = options['days']
        today = datetime.date.today()
        self.stdout.write('Starting Garmin sync...')
        
        # Login
        api = Garmin(os.getenv('GARMIN_EMAIL'), os.getenv('GARMIN_PASSWORD'))
        api.login()
        
        self._sync_ftp(api) # ftp not date-specific

        # Define Date Range (Syncing last 4 days to catch delayed uploads)
        today = datetime.date.today()
        for i in range(days, -1, -1):
            date_str = (today - datetime.timedelta(days=i)).isoformat()
            self.stdout.write(f"--- Checking date: {date_str} ---")
            self._sync_activities(api, date_str)
            self._sync_sleep(api, date_str) 
            self._sync_hrv(api, date_str)
            self._sync_daily_stats(api, date_str)
            time.sleep(2)  # Sleep to avoid hitting API rate limits
        
        self.stdout.write(self.style.SUCCESS('Garmin Sync complete'))


    def _sync_activities(self, api, date):
        activities = api.get_activities_by_date(date, date)

        for activity in activities:
            garmin_id = str(activity['activityId'])
            activity_type = activity.get('activityType', {}).get('typeKey', 'other')

            defaults = {
                # --- Identification ---
                'activity_name': activity.get('activityName'),
                'activity_type': activity_type,
                'start_time': make_aware(datetime.datetime.strptime(
                    activity['startTimeLocal'], "%Y-%m-%d %H:%M:%S"
                )),
                'location_name': activity.get('locationName'),
                'device_id': str(activity.get('deviceId', '')),

                # --- Primary Metrics ---
                'duration_seconds': activity.get('duration'),
                'moving_duration_seconds': activity.get('movingDuration'),
                'elapsed_duration_seconds': activity.get('elapsedDuration'),
                'distance_meters': activity.get('distance'),
                'calories': int(activity['calories']) if activity.get('calories') else None,
                'bmr_calories': int(activity['bmrCalories']) if activity.get('bmrCalories') else None,

                # --- Heart Rate ---
                'avg_hr': int(activity['averageHR']) if activity.get('averageHR') else None,
                'max_hr': int(activity['maxHR']) if activity.get('maxHR') else None,
                'hr_zone_1_seconds': activity.get('hrTimeInZone_1'),
                'hr_zone_2_seconds': activity.get('hrTimeInZone_2'),
                'hr_zone_3_seconds': activity.get('hrTimeInZone_3'),
                'hr_zone_4_seconds': activity.get('hrTimeInZone_4'),
                'hr_zone_5_seconds': activity.get('hrTimeInZone_5'),

                # --- Training Analysis ---
                'training_load': activity.get('activityTrainingLoad'),
                'training_effect_aerobic': activity.get('aerobicTrainingEffect'),
                'training_effect_anaerobic': activity.get('anaerobicTrainingEffect'),
                'training_effect_label': activity.get('trainingEffectLabel'),
                'vo2_max': activity.get('vO2MaxValue'),

                # --- Environment ---
                'elevation_gain_m': activity.get('elevationGain'),
                'elevation_loss_m': activity.get('elevationLoss'),
                'min_temp': activity.get('minTemperature'),
                'max_temp': activity.get('maxTemperature'),
                'body_battery_delta': activity.get('differenceBodyBattery'),
                'lap_count': activity.get('lapCount'),

                # --- Strength Training ---
                'total_sets': activity.get('totalSets'),
                'active_sets': activity.get('activeSets'),
                'total_reps': activity.get('totalReps'),

                # --- Cycling (confirmed in summary) ---
                'avg_power': int(activity['avgPower']) if activity.get('avgPower') else None,
                'max_power': int(activity['maxPower']) if activity.get('maxPower') else None,
                'normalized_power': int(activity['normPower']) if activity.get('normPower') else None,
                'tss': activity.get('trainingStressScore'),
                'intensity_factor': activity.get('intensityFactor'),
                'avg_bike_cadence': int(activity['averageBikingCadenceInRevPerMinute']) if activity.get('averageBikingCadenceInRevPerMinute') else None,
                'max_bike_cadence': int(activity['maxBikingCadenceInRevPerMinute']) if activity.get('maxBikingCadenceInRevPerMinute') else None,
                'power_zone_1_seconds': activity.get('powerTimeInZone_1'),
                'power_zone_2_seconds': activity.get('powerTimeInZone_2'),
                'power_zone_3_seconds': activity.get('powerTimeInZone_3'),
                'power_zone_4_seconds': activity.get('powerTimeInZone_4'),
                'power_zone_5_seconds': activity.get('powerTimeInZone_5'),
                'power_zone_6_seconds': activity.get('powerTimeInZone_6'),
            }

            # Running dynamics only — these come from details endpoint
            try:
                details = api.get_activity(int(garmin_id))
                time.sleep(2)
                defaults.update(self._parse_sport_specifics(details, activity_type))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Could not fetch details for {garmin_id}: {e}"
                ))

            obj, created = Activity.objects.update_or_create(
                garmin_id=garmin_id,
                defaults=defaults
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"  [{status}] {activity_type}: {defaults['activity_name']}")

        self.stdout.write(f'  Activities synced: {len(activities)}')


    def _parse_sport_specifics(self, details, activity_type):
        """
        Only called for fields that are NOT in the summary.
        Currently only running dynamics from HRM Pro.
        Cycling and strength fields are already handled in defaults.
        """
        fields = {}

        if any(s in activity_type for s in ['running', 'treadmill']):
            fields['avg_running_cadence'] = details.get('averageRunningCadenceInStepsPerMinute') or details.get('averageRunCadence')
            fields['max_running_cadence'] = details.get('maxRunningCadenceInStepsPerMinute') or details.get('maxRunCadence')
            fields['avg_stride_length_cm'] = details.get('avgStrideLength') or details.get('strideLength')
            fields['avg_vertical_oscillation_cm'] = details.get('avgVerticalOscillation') or details.get('verticalOscillation')
            fields['avg_vertical_ratio'] = details.get('avgVerticalRatio') or details.get('verticalRatio')
            fields['avg_ground_contact_time_ms'] = details.get('avgGroundContactTime') or details.get('groundContactTime')
            fields['avg_ground_contact_balance_left'] = details.get('avgGroundContactBalance')
            fields['avg_running_power'] = details.get('avgPower') or details.get('averagePower')
            fields['avg_grade_adjusted_speed'] = details.get('avgGradeAdjustedSpeed') or details.get('gradeAdjustedSpeed')

        return fields

    # STUBS for remaining sync methods
    def _sync_sleep(self, api, date):
        try:
            # api.get_sleep_data returns a dictionary containing 'dailySleepDTO'
            data = api.get_sleep_data(date)
            dto = data.get('dailySleepDTO')

            if not dto:
                self.stdout.write(f"  [No Data] No sleep data found for {date}")
                return

            # Extracting the score safely from the nested sleepScores dictionary
            sleep_scores = dto.get('sleepScores', {})
            overall_score = sleep_scores.get('overall', {}).get('value')

            # bodyBatteryChange is typically at the top level of the sleep response
            # or calculated as bodyBatteryDuringSleep
            bb_change = data.get('bodyBatteryChange')

            # Map JSON to SleepRecord Model
            obj, created = SleepRecord.objects.update_or_create(
                date=dto.get('calendarDate'),
                defaults={
                    'duration_hours': dto.get('sleepTimeSeconds', 0) / 3600.0 if dto.get('sleepTimeSeconds') else None,
                    'score': overall_score if overall_score is not None else None,
                    'deep_sleep_hours': dto.get('deepSleepSeconds', 0) / 3600.0 if dto.get('deepSleepSeconds') else None,
                    'rem_sleep_hours': dto.get('remSleepSeconds', 0) / 3600.0 if dto.get('remSleepSeconds') else None,
                    'light_sleep_hours': dto.get('lightSleepSeconds', 0) / 3600.0 if dto.get('lightSleepSeconds') else None,
                    'awake_hours': dto.get('awakeSleepSeconds', 0) / 3600.0 if dto.get('awakeSleepSeconds') else None,
                    'body_battery_change': bb_change if bb_change is not None else None,
                }
            )

            status = "Created" if created else "Updated"
            self.stdout.write(f"  [{status}] Sleep for {date}: Score {overall_score or 'N/A'}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error syncing Sleep on {date}: {e}"))

    def _sync_hrv(self, api, date):
        # api.get_hrv_data returns a list or dict depending on the library version
        # but based on your snippet, we are looking for the 'hrvSummary' key.
        try:
            data = api.get_hrv_data(date)
            if not data:
                self.stdout.write(f"  [No Data] No HRV data found for {date}")
                return

            summary = data.get('hrvSummary')
            
            if summary and summary.get('lastNightAvg'):
                # Garmin returns 'BALANCED', model expects 'balanced'
                raw_status = summary.get('status')
                formatted_status = raw_status.lower() if raw_status else None

                HRVRecord.objects.update_or_create(
                    date=summary.get('calendarDate'), # Use the date from the API response
                    defaults={
                        'hrv_rmssd': summary.get('lastNightAvg') if summary.get('lastNightAvg') is not None else None,
                        'hrv_status': formatted_status if formatted_status in dict(HRVRecord.HRV_STATUS_CHOICES) else None,
                        'resting_hr': data.get('restingHeartRate') if data.get('restingHeartRate') is not None else None, # Note: resting_hr is usually in daily_stats, not this HRV summary
                    }
                )
                self.stdout.write(f"  [Updated] HRV for {date}: {summary.get('lastNightAvg')}ms ({raw_status})")
            else:
                self.stdout.write(f"  [No Data] HRV Summary is empty for {date}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error syncing HRV: {e}"))

    def _sync_daily_stats(self, api, date):
        try:
            data = api.get_stats(date)
            if not data:
                self.stdout.write(f"  [No Data] Daily stats not found for {date}")
                return

            # --- VO2max + training status (separate endpoint, nested) ---
            vo2_running = None
            vo2_cycling = None
            training_status_val = None
            acwr_ratio = None

            try:
                ts = api.get_training_status(date)
                time.sleep(1)

                vo2_block = ts.get('mostRecentVO2Max') or {}
                generic = vo2_block.get('generic') or {}
                cycling = vo2_block.get('cycling') or {}
                vo2_running = generic.get('vo2MaxValue')
                vo2_cycling = cycling.get('vo2MaxValue')

                status_block = ts.get('mostRecentTrainingStatus') or {}
                status_map = status_block.get('latestTrainingStatusData') or {}
                if status_map:
                    device_data = list(status_map.values())[0]
                    training_status_val = device_data.get('trainingStatus')
                    acwr = device_data.get('acuteTrainingLoadDTO') or {}
                    acwr_ratio = acwr.get('dailyAcuteChronicWorkloadRatio')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Training status failed for {date}: {e}"))

            # --- Endurance score (separate endpoint) ---
            endurance_score = None
            try:
                es = api.get_endurance_score(date)
                time.sleep(1)
                if es:
                    endurance_score = es.get('overallScore')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Endurance score failed for {date}: {e}"))

            DailyStats.objects.update_or_create(
                date=data.get('calendarDate'),
                defaults={
                    'body_battery_high': data.get('bodyBatteryHighestValue'),
                    'body_battery_low': data.get('bodyBatteryLowestValue'),
                    'stress_level_avg': data.get('averageStressLevel'),
                    'steps': data.get('totalSteps'),
                    'total_calories': int(data['totalKilocalories']) if data.get('totalKilocalories') else None,
                    'vo2max_running': vo2_running,
                    'vo2max_cycling': vo2_cycling,
                    'training_status': training_status_val,
                    'acwr_ratio': acwr_ratio,
                    'endurance_score': endurance_score,
                }
            )

            resting_hr = data.get('restingHeartRate')
            if resting_hr:
                HRVRecord.objects.filter(date=data.get('calendarDate')).update(resting_hr=resting_hr)

            self.stdout.write(f"  [Updated] Daily Stats for {date}: VO2 run {vo2_running} / cyc {vo2_cycling}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  Error syncing Daily Stats: {e}"))

    def _sync_ftp(self, api):
        try:
            from sync.models import UserProfile, FTPRecord
            ftp_data = api.get_cycling_ftp()
            if ftp_data and ftp_data.get('functionalThresholdPower'):
                ftp = ftp_data['functionalThresholdPower']

                # Update current value in profile
                profile, _ = UserProfile.objects.get_or_create(pk=1)
                profile.ftp_watts = ftp
                profile.save()

                # Store history — calendarDate is when FTP was set
                ftp_date = ftp_data.get('calendarDate', '')[:10]  # "2026-06-06"
                if ftp_date:
                    FTPRecord.objects.update_or_create(
                        date=ftp_date,
                        defaults={'ftp_watts': ftp}
                    )

                self.stdout.write(f"  FTP synced: {ftp}W ({ftp_date})")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  FTP sync failed: {e}"))

if __name__ == "__main__":
    command = Command()
    command.handle()