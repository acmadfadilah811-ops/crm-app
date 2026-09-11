"""
Celery Beat schedule for horilla_booking.
"""

from datetime import timedelta

HORILLA_BEAT_SCHEDULE = {
    "send-booking-reminders-every-15min": {
        "task": "booking.tasks.send_booking_reminders",
        "schedule": timedelta(minutes=15),
    },
}
