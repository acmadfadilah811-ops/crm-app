"""Admin configuration for calendar app."""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import (
    CustomCalendar,
    CustomCalendarCondition,
    GoogleCalendarConfig,
    GoogleIntegrationSetting,
    UserAvailability,
    UserCalendarPreference,
)

admin.site.register(UserCalendarPreference)
admin.site.register(UserAvailability)
admin.site.register(CustomCalendar)
admin.site.register(CustomCalendarCondition)
admin.site.register(GoogleCalendarConfig)
admin.site.register(GoogleIntegrationSetting)
