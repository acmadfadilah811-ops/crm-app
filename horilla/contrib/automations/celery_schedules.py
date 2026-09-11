"""
Celery beat schedule configuration for automations app.

This hooks into Horilla's AppLauncher auto-merge of beat schedules:
- automations/apps.py sets celery_schedule_module="celery_schedules"
- AppLauncher merges HORILLA_BEAT_SCHEDULE into settings.CELERY_BEAT_SCHEDULE at startup
"""

# Standard library imports
from datetime import timedelta

HORILLA_BEAT_SCHEDULE = {
    "run-scheduled-automations-every-minute": {
        "task": "horilla.contrib.automations.tasks.run_scheduled_automations",
        "schedule": timedelta(minutes=1),
    },
}
