"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the keys app
"""

from horilla.menu import my_settings_menu

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Define your menu registration logic here


@my_settings_menu.register
class ShortKeySettings:
    """'My Settings' menu entry for Short Keys."""

    title = _("Short Keys")
    url = reverse_lazy("keys:short_key_view")
    active_urls = [
        "keys:short_key_view",
    ]
    hx_select_id = "#short-key-view"
    order = 6
    perm = ["keys.view_shortcutkey", "keys.view_own_shortcutkey"]
    attrs = {
        "hx-boost": "true",
        "hx-target": "#my-settings-content",
        "hx-push-url": "true",
        "hx-select": "#short-key-view",
        "hx-select-oob": "#my-settings-sidebar",
    }
