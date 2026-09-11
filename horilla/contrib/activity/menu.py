"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the Horilla  Activities app
"""

from horilla.menu import MAIN_CONTENT_HX_ATTRS, sub_section_menu

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _


@sub_section_menu.register
class ActivitySubSection:
    """
    Registers the activity menu to sub section in the main sidebar.
    """

    # Identity / placement
    section = "schedule"
    app_label = "activity"
    position = 2

    # Display
    verbose_name = _("Activities")
    icon = "/assets/icons/activity.svg"

    # Behavior
    url = reverse_lazy("activity:activity_view")
    attrs = MAIN_CONTENT_HX_ATTRS

    # Access control
    perm = ["activity.view_activity", "activity.view_own_activity"]
