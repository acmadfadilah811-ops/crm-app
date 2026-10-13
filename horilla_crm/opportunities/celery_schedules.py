"""Jadwal Celery beat modul opportunities (digabung otomatis oleh AppLauncher)."""

from celery.schedules import crontab

HORILLA_BEAT_SCHEDULE = {
    # 01:00 UTC = 08:00 WIB, sebelum jam kerja.
    "sinkron-follow-up-pelanggan-harian": {
        "task": "horilla_crm.opportunities.tasks.sinkron_follow_up_pelanggan",
        "schedule": crontab(hour=1, minute=0),
    },
}
