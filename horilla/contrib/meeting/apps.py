"""Configuration for the meeting integration app in Horilla."""

from horilla.apps import AppLauncher
from horilla.utils.translation import gettext_lazy as _


class MeetingConfig(AppLauncher):
    """App configuration for the Horilla Meeting Integration app."""

    default = True
    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla.contrib.meeting"
    label = "meeting"
    verbose_name = _("Meeting Integration")

    url_prefix = "meeting/"
    url_module = "horilla.contrib.meeting.urls"
    url_namespace = "meeting"

    auto_import_modules = [
        "menu",
        "signals",
    ]
