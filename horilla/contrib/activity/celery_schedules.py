"""Celery beat schedule for the activity app."""

from datetime import timedelta

HORILLA_BEAT_SCHEDULE = {
    "send-meeting-reminders-every-minute": {
        "task": "horilla.contrib.activity.tasks.send_meeting_reminders",
        "schedule": timedelta(minutes=1),
    },
}
