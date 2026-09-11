"""
Admin registration for the theme app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import CompanyTheme, HorillaColorTheme

# Register your theme models here.
admin.site.register(HorillaColorTheme)
admin.site.register(CompanyTheme)
