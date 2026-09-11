"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the cadences app
"""

from horilla.contrib.automations.menu import AutomationSettings

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Define your menu registration logic here

automation = AutomationSettings
automation.items.extend(
    [
        {
            "label": _("Cadences"),
            "url": reverse_lazy("cadences:cadence_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#cadence-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "cadences.view_cadence",
            "order": 2,
        },
    ]
)
