"""
AppLauncher for the horilla.contrib.theme app
"""

# First party imports (Horilla)
from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _


class ThemeConfig(AppLauncher):
    """App configuration class for horilla.contrib.theme."""

    default = True

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla.contrib.theme"
    label = "theme"
    verbose_name = _("Theme Manager")

    auto_import_modules = [
        "menu",
        "signals",
        "registration",
    ]

    url_prefix = "theme/"
    url_module = "horilla.contrib.theme.urls"
    url_namespace = "theme"
