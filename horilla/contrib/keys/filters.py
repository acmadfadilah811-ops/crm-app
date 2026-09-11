"""
Filters for the keys app.
"""

# First party imports (Horilla)
from horilla.contrib.generics.filters import HorillaFilterSet

# Local imports
from .models import ShortcutKey


class ShortKeyFilter(HorillaFilterSet):
    """
    Filter set for ShortcutKey model.

    Used to filter, search, and manage shortcut key records
    across the application.
    """

    class Meta:
        """
        Meta configuration for ShortKeyFilter.
        """

        model = ShortcutKey
        fields = "__all__"
        exclude = ["additional_info"]
        search_fields = ["page"]
