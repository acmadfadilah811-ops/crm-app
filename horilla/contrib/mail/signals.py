"""
mail signals module
"""

# Third-party imports (Django)
from django.dispatch import receiver

# First party imports (Horilla)
from horilla.db.models.signals import post_delete

# Local imports
from .models import HorillaMailAttachment

# Define your mail signals here


@receiver(post_delete, sender=HorillaMailAttachment)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Deletes file from storage when HorillaMailAttachment is deleted."""
    if instance.file:
        storage, path = instance.file.storage, instance.file.path
        if storage.exists(path):
            storage.delete(path)
