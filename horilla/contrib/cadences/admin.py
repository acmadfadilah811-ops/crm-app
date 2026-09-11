"""
Admin registration for the cadences app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import Cadence, CadenceFollowUp

admin.site.register(Cadence)
admin.site.register(CadenceFollowUp)

# Register your cadences models here.
