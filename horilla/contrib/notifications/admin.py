"""
Django admin configuration for notifications app.

This module registers the Notification model with the Django admin interface,
allowing administrators to manage notifications through the admin panel.
"""

# notifications/admin.py

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import Notification, NotificationSoundPreference, NotificationTemplate

admin.site.register(Notification)
admin.site.register(NotificationTemplate)
admin.site.register(NotificationSoundPreference)

# Register your notifications models here.
