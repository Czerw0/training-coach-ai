# Run with:  python manage.py sync_indoor_workouts
# Parsed from the MyWhoosh .zwo files. Intervals are % FTP, flattened.

from django.core.management.base import BaseCommand
from sync.models import IndoorCyclingWorkout


WORKOUTS = [
    {
        "name": "15min Varied Tempo #1",
        "category": "tempo",
        "duration_min": 48,
        "intensity_factor": 0.81,
        "tss": 53,
        "description": "Today, working in your Zone 3 Tempo, we vary the cadence and power. Observe your Heart Rate during the 15-minute interval and look for changes in your Heart Rate when the cadence varies. We are working at the lower end of the training Zone today. The added stress comes from the target cadence.",
        "structure": [
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 57,
                "ftp_high": 57,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 81,
                "ftp_high": 81,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 56,
                "ftp_high": 56,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 86,
                "ftp_high": 86,
                "cadence": 90
            },
            {
                "sec": 300,
                "ftp_low": 85,
                "ftp_high": 85,
                "cadence": 95
            },
            {
                "sec": 300,
                "ftp_low": 85,
                "ftp_high": 85,
                "cadence": 100
            },
            {
                "sec": 300,
                "ftp_low": 56,
                "ftp_high": 56,
                "cadence": None
            },
            {
                "sec": 100,
                "ftp_low": 93,
                "ftp_high": 93,
                "cadence": None
            },
            {
                "sec": 100,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            }
        ]
    },
    {
        "name": "5min Max Aerobic",
        "category": "vo2max",
        "duration_min": 62,
        "intensity_factor": 0.85,
        "tss": 75,
        "description": "By working just above Threshold in Zone 4 and into Zone 5, we can improve our VO2max abilities and increase our Threshold. These are high-intensity efforts, so the intervals are broken down into shorter work periods. A well developed VO2max system will allow you to recover from high-intensity efforts faster and increase endurance.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 57,
                "ftp_high": 57,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 63,
                "ftp_high": 63,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 600,
                "ftp_low": 71,
                "ftp_high": 45,
                "cadence": None
            }
        ]
    },
    {
        "name": "90 Minute Endurance",
        "category": "endurance",
        "duration_min": 90,
        "intensity_factor": 0.69,
        "tss": 71,
        "description": "Zone 2 endurance training is one of the most important aspects of any training plan. In this training Zone, we predominately stimulate Type 1 muscle fibres, leading to increased mitochondrial growth and function. You improve your ability to utilise fat as the preferred fuel source and preserve your precious glycogen stores. Long periods within Zone 2 will benefit any athlete. Feel free to substitute this structured endurance ride with a low-intensity free ride. Or jump into a low-intensity group ride if available. Choose a course or group ride that will allow you to spend most of your ride with Zone 2.",
        "structure": [
            {
                "sec": 180,
                "ftp_low": 39,
                "ftp_high": 59,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 40,
                "ftp_high": 40,
                "cadence": None
            }
        ]
    },
    {
        "name": "A forest",
        "category": "endurance",
        "duration_min": 46,
        "intensity_factor": 0.8,
        "tss": 49,
        "description": "The challenge today is to reach the target power with the highest cadence possible.",
        "structure": [
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 56,
                "ftp_high": 56,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 69,
                "ftp_high": 69,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            }
        ]
    },
    {
        "name": "AC + Sweetspot #1",
        "category": "sweetspot",
        "duration_min": 62,
        "intensity_factor": 0.98,
        "tss": 99,
        "description": "The aim today is to work on your Anaerobic Capacity and improve your aerobic efficiency. We do this by completing 5 x 2min AC intervals before finishing with a 10min Sweetspot effort. By depleting your carbohydrate stores with the AC intervals, the 10min Sweetspot effort may not be as comfortable as it should be!",
        "structure": [
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 180,
                "ftp_high": 180,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 60,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 90,
                "ftp_high": 104,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 143,
                "ftp_high": 143,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 136,
                "ftp_high": 136,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 129,
                "ftp_high": 129,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 122,
                "ftp_high": 122,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 600,
                "ftp_low": 94,
                "ftp_high": 88,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 45,
                "cadence": None
            }
        ]
    },
    {
        "name": "Active Recovery",
        "category": "recovery",
        "duration_min": 48,
        "intensity_factor": 0.63,
        "tss": 32,
        "description": "Don't discount the importance of today! This is where the magic happens, and the gains are realised. Recovery rides allow your body to recuperate and adapt, increasing your fitness. Enjoy today. You deserve it!",
        "structure": [
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 600,
                "ftp_low": 60,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 600,
                "ftp_low": 60,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            }
        ]
    },
    {
        "name": "Aerobic Ramps",
        "category": "endurance",
        "duration_min": 53,
        "intensity_factor": 0.71,
        "tss": 45,
        "description": "One of the most important aspects of cycling is your aerobic fitness. Not every session needs to involve high-intensity efforts. Today's session is a low-intensity workout focussing on your aerobic fitness. This allows you to preserve vital glycogen stores and power up the day's final climb.",
        "structure": [
            {
                "sec": 180,
                "ftp_low": 45,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 81,
                "ftp_high": 81,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 88,
                "ftp_high": 88,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 61,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 60,
                "ftp_high": 60,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 61,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 61,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 61,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 61,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 50,
                "cadence": None
            }
        ]
    },
    {
        "name": "All I need",
        "category": "endurance",
        "duration_min": 20,
        "intensity_factor": 0.74,
        "tss": 18,
        "description": "Quite often, racing involves periods of short, high-intensity efforts, followed by a period of Tempo riding.",
        "structure": [
            {
                "sec": 240,
                "ftp_low": 45,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 81,
                "ftp_high": 81,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            },
            {
                "sec": 420,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 55,
                "ftp_high": 55,
                "cadence": None
            }
        ]
    },
    {
        "name": "Base Miles #1",
        "category": "endurance",
        "duration_min": 42,
        "intensity_factor": 0.66,
        "tss": 30,
        "description": "Low-intensity Base Miles is a great way to build fitness. The effort is low enough that we can complete moderate duration frequently. To improve your response to this type of training, we also focus on your cadence. Today, we perform a long, steady base ride with varying cadence to improve your training response.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 40,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 62,
                "ftp_high": 62,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 62,
                "ftp_high": 62,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 62,
                "ftp_high": 62,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 66,
                "ftp_high": 40,
                "cadence": None
            }
        ]
    },
    {
        "name": "Depleting Session #1",
        "category": "endurance",
        "duration_min": 34,
        "intensity_factor": 0.77,
        "tss": 34,
        "description": "Large amounts of tempo work in today's session, but the focus is on fuel. To produce zone 3 power and above requires a significant amount of glycogen. But what happens when this fuel source has been depleted?",
        "structure": [
            {
                "sec": 240,
                "ftp_low": 45,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 91,
                "ftp_high": 91,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 91,
                "ftp_high": 91,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 91,
                "ftp_high": 91,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 480,
                "ftp_low": 78,
                "ftp_high": 78,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            }
        ]
    },
    {
        "name": "Endurance #2",
        "category": "endurance",
        "duration_min": 62,
        "intensity_factor": 0.76,
        "tss": 60,
        "description": "Long, low-intensity efforts aren't the only method to build endurance. Incorporating short surges into a steady effort will increase your oxygen uptake and training stimulus. Completing a low-intensity effort with a surge every 4 minutes should feel comfortable, but the constant change in power and surging will provide you with significant gains in endurance.",
        "structure": [
            {
                "sec": 360,
                "ftp_low": 45,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 90,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 90,
                "ftp_high": 90,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 56,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 45,
                "cadence": None
            }
        ]
    },
    {
        "name": "Endurance into Max Aerobic",
        "category": "vo2max",
        "duration_min": 38,
        "intensity_factor": 0.77,
        "tss": 38,
        "description": "After a good warm-up, we are going to build some endurance and fatigue before preparing yourself for a Max Aerobic interval. We can't always start the intervals with fresh legs. The session provides a different training stimulus by including Zone 2 endurance before the high-intensity work.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 45,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 10,
                "ftp_low": 150,
                "ftp_high": 150,
                "cadence": None
            },
            {
                "sec": 50,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 103,
                "ftp_high": 103,
                "cadence": None
            },
            {
                "sec": 900,
                "ftp_low": 65,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 85,
                "ftp_high": 85,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 70,
                "ftp_high": 45,
                "cadence": None
            }
        ]
    },
    {
        "name": "Ramp Test - MyWhoosh",
        "category": "testing",
        "duration_min": 37,
        "intensity_factor": 1.15,
        "tss": 82,
        "description": "Welcome to the MyWhoosh Ramp test! Today we measure your Maximal Aerobic Power by ramping up the power every minute until exhaustion. We use your peak 1min power to calculate your FTP from this effort. This testing method takes less time to complete than the traditional 20min FTP test, and it also removes the component of pacing from the effort. After completing a low-intensity 5min warmup, the power will increase each minute until you reach failure. It's not necessary to complete each step. Your FTP will be calculated from your peak 1min power produced. It is important to remain seated for this test to provide accurate results. Be prepared; the test starts comfortably but quickly changes! NOTE: ERG mode MUST be on.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 46,
                "ftp_high": 46,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 52,
                "ftp_high": 52,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 58,
                "ftp_high": 58,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 64,
                "ftp_high": 64,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 76,
                "ftp_high": 76,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 82,
                "ftp_high": 82,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 88,
                "ftp_high": 88,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 94,
                "ftp_high": 94,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 100,
                "ftp_high": 100,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 106,
                "ftp_high": 106,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 112,
                "ftp_high": 112,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 118,
                "ftp_high": 118,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 124,
                "ftp_high": 124,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 130,
                "ftp_high": 130,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 136,
                "ftp_high": 136,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 142,
                "ftp_high": 142,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 148,
                "ftp_high": 148,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 154,
                "ftp_high": 154,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 160,
                "ftp_high": 160,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 166,
                "ftp_high": 166,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 172,
                "ftp_high": 172,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 178,
                "ftp_high": 178,
                "cadence": None
            },
            {
                "sec": 600,
                "ftp_low": 46,
                "ftp_high": 46,
                "cadence": None
            }
        ]
    },
    {
        "name": "Stepping up",
        "category": "endurance",
        "duration_min": 44,
        "intensity_factor": 0.77,
        "tss": 43,
        "description": "Interval training can also include more than 1 Training Zone in a structured effort. Stepped intervals require you to progress your way through the various Zones. Generally, the duration of each interval is decreased as the intensity increases. Today's session will you see step through Zones 2, 3, 4 and 5.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 40,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 71,
                "ftp_high": 71,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 82,
                "ftp_high": 82,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 240,
                "ftp_low": 82,
                "ftp_high": 82,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 109,
                "ftp_high": 109,
                "cadence": None
            },
            {
                "sec": 420,
                "ftp_low": 75,
                "ftp_high": 42,
                "cadence": None
            }
        ]
    },
    {
        "name": "Sub Threshold #1",
        "category": "threshold",
        "duration_min": 55,
        "intensity_factor": 0.81,
        "tss": 60,
        "description": "We need to perform long, steady efforts to build endurance and aerobic efficiency. Today's session is comprised of 2 x 10-minute Sub Threshold efforts. After opening the interval with a 30-second zone 5 surge, the remaining time will gradually increase in power throughout the effort. Observe how much this increase in power affects your heart rate.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 45,
                "ftp_high": 75,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 98,
                "ftp_high": 98,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 98,
                "ftp_high": 98,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 95,
                "ftp_high": 95,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": None
            },
            {
                "sec": 570,
                "ftp_low": 88,
                "ftp_high": 94,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": None
            },
            {
                "sec": 570,
                "ftp_low": 88,
                "ftp_high": 94,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 75,
                "ftp_high": 45,
                "cadence": None
            }
        ]
    },
    {
        "name": "Train Like Tadej-4x3min VO2 Max",
        "category": "vo2max",
        "duration_min": 57,
        "intensity_factor": 0.8,
        "tss": 61,
        "description": "Train Like Tadej for the Giro-Tour Double with 4x3min VO2 Max. These intervals are short and challenging at 110% FTP. There is an extra minute added onto each section of recovery to allow you to fully catch your breath. This is a great pre-race session that targets the upper limits of your repeatable VO2 Max power.",
        "structure": [
            {
                "sec": 300,
                "ftp_low": 40,
                "ftp_high": 65,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 70,
                "ftp_high": 70,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 90,
                "ftp_high": 90,
                "cadence": None
            },
            {
                "sec": 300,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": 90
            },
            {
                "sec": 240,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": 85
            },
            {
                "sec": 180,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": 90
            },
            {
                "sec": 240,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": 85
            },
            {
                "sec": 180,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": 90
            },
            {
                "sec": 240,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": 85
            },
            {
                "sec": 180,
                "ftp_low": 110,
                "ftp_high": 110,
                "cadence": 90
            },
            {
                "sec": 240,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": 85
            },
            {
                "sec": 600,
                "ftp_low": 60,
                "ftp_high": 35,
                "cadence": None
            }
        ]
    },
    {
        "name": "Train like Tadej - Short climbs",
        "category": "endurance",
        "duration_min": 53,
        "intensity_factor": 0.81,
        "tss": 58,
        "description": "How does Tadej Pogacar train to perform those explosive race-winning attacks? This workout by the UAE Team Emirates coach focuses on VO2max power and the ability to repeat this. The ability to perform race-winning efforts late in the race is critical to success. To achieve this, we begin with a long Zone 2 interval followed by high-intensity VO2max efforts.",
        "structure": [
            {
                "sec": 240,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 45,
                "ftp_high": 45,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 45,
                "ftp_high": 45,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 45,
                "ftp_high": 45,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 80,
                "ftp_high": 80,
                "cadence": None
            },
            {
                "sec": 30,
                "ftp_low": 45,
                "ftp_high": 45,
                "cadence": None
            },
            {
                "sec": 60,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 900,
                "ftp_low": 73,
                "ftp_high": 73,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 107,
                "ftp_high": 107,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 107,
                "ftp_high": 107,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 107,
                "ftp_high": 107,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 107,
                "ftp_high": 107,
                "cadence": None
            },
            {
                "sec": 180,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            },
            {
                "sec": 120,
                "ftp_low": 50,
                "ftp_high": 50,
                "cadence": None
            }
        ]
    }
]


class Command(BaseCommand):
    help = "Load / update the indoor cycling workout library."

    def handle(self, *args, **options):
        created = updated = 0
        for w in WORKOUTS:
            _, was_created = IndoorCyclingWorkout.objects.update_or_create(
                name=w["name"],
                defaults={
                    "category": w["category"],
                    "duration_min": w["duration_min"],
                    "intensity_factor": w["intensity_factor"],
                    "tss": w["tss"],
                    "description": w["description"],
                    "structure": w["structure"],
                },
            )
            created += was_created
            updated += (not was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Done. {created} created, {updated} updated, {len(WORKOUTS)} total."
        ))