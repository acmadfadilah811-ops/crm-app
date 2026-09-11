"""
Admin registration for the keys app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import ShortcutKey

# Register your keys models here.

admin.site.register(ShortcutKey)
