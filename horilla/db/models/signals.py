"""
Horilla database model signals — re-exports django.db.models.signals.

Use: from horilla.db.models.signals import post_save, pre_save
Or:  from horilla.db.models import signals  (submodule namespace for .connect())
"""

from django.db.models.signals import (
    ModelSignal,
    Signal,
    class_prepared,
    m2m_changed,
    post_delete,
    post_init,
    post_migrate,
    post_save,
    pre_delete,
    pre_init,
    pre_migrate,
    pre_save,
)

__all__ = [
    "ModelSignal",
    "Signal",
    "class_prepared",
    "m2m_changed",
    "post_delete",
    "post_init",
    "post_migrate",
    "post_save",
    "pre_delete",
    "pre_init",
    "pre_migrate",
    "pre_save",
]
