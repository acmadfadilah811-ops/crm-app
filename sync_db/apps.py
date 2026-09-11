"""Django application config for sync_db helpers."""

from django.apps import AppConfig


class SyncdbConfig(AppConfig):
    """Registers the sync_db contrib package with Django."""

    name = "sync_db"
