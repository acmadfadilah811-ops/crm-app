"""
Admin registration for the automations app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import AutomationCondition, AutomationRunLog, HorillaAutomation

# Register your automations models here.


@admin.register(HorillaAutomation)
class HorillaAutomationAdmin(admin.ModelAdmin):
    """Admin configuration for HorillaAutomation."""

    filter_horizontal = ("also_sent_to",)


admin.site.register(AutomationCondition)
admin.site.register(AutomationRunLog)
