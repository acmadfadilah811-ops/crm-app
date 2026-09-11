"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the theme app
"""

from horilla.menu import settings_menu

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Local imports
from .apps import ThemeConfig
from .models import HorillaColorTheme

# Define your menu registration logic here


@settings_menu.register
class ThemeSettings:
    """Settings menu for Theme settings module"""

    title = ThemeConfig.verbose_name
    icon = "/theme/assets/icons/theme.svg"
    order = 7
    items = [
        {
            "label": HorillaColorTheme()._meta.verbose_name,
            "url": reverse_lazy("theme:color_theme_view"),
            "hx-push-url": "true",
            "hx-target": "#settings-content",
            "hx-select": "#theme-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "theme.view_horillacolortheme",
        },
    ]
