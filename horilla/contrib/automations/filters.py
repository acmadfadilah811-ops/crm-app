"""
Filters for the automations app
"""

# First party imports (Horilla)
from horilla.contrib.generics.filters import HorillaFilterSet

# Local imports
from .models import HorillaAutomation

# Define your automations filters here


class HorillaAutomationFilter(HorillaFilterSet):
    """Filter set for HorillaMailConfiguration model."""

    class Meta:
        """Meta class for HorillaMailServerFilter."""

        model = HorillaAutomation
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["title"]
