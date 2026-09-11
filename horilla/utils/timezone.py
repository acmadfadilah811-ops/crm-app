"""
Horilla timezone utilities — re-exports django.utils.timezone.

Use: from horilla.utils import timezone
     timezone.now()
"""

from django.utils.timezone import (
    UTC,
    activate,
    deactivate,
    get_current_timezone,
    get_current_timezone_name,
    get_default_timezone,
    get_default_timezone_name,
    get_fixed_timezone,
    is_aware,
    is_naive,
    localdate,
    localtime,
    make_aware,
    make_naive,
    now,
    override,
    template_localtime,
)

__all__ = [
    "UTC",
    "activate",
    "deactivate",
    "get_current_timezone",
    "get_current_timezone_name",
    "get_default_timezone",
    "get_default_timezone_name",
    "get_fixed_timezone",
    "is_aware",
    "is_naive",
    "localdate",
    "localtime",
    "make_aware",
    "make_naive",
    "now",
    "override",
    "template_localtime",
]
