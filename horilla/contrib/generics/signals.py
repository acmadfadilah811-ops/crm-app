"""
Signal handlers for horilla.contrib.generics.

Defines signal receivers to keep caches and related state in sync.
"""

from django.core.cache import cache

# Third-party imports (Django)
from django.dispatch import receiver

from horilla.contrib.core.models import ListColumnVisibility

# First party imports (Horilla)
from horilla.db.models.signals import post_delete

# Define your horilla.contrib.generics signals here


@receiver(post_delete, sender=ListColumnVisibility)
def clear_cache_on_delete(sender, instance, **kwargs):
    """
    Clear the cache for the corresponding ListColumnVisibility object when it is deleted.
    """
    cache_key = f"visible_columns_{instance.user.id}_{instance.app_label}_{instance.model_name}_{instance.context}_{instance.url_name}"
    cache.delete(cache_key)
