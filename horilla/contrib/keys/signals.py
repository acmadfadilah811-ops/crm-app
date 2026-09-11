"""
Signals for the keys app
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.dispatch import receiver

from horilla.apps import apps
from horilla.auth.models import User

# First party imports (Horilla)
from horilla.db.models.signals import post_migrate, post_save
from horilla.urls import NoReverseMatch, reverse_lazy

# Local imports
from .models import ShortcutKey
from .utils import normalize_page_url

logger = logging.getLogger(__name__)

DEFAULT_SHORTCUTS = [
    {"page": "/", "key": "H", "command": "alt"},
    {"page": "/my-profile-view/", "key": "P", "command": "alt"},
    {"page": "/regional-formating-view/", "key": "G", "command": "alt"},
    {"page": "/user-login-history-view/", "key": "L", "command": "alt"},
    {"page": "/user-holiday-view/", "key": "V", "command": "alt"},
    {"page": "/shortkeys/short-key-view/", "key": "K", "command": "alt"},
    {"page": "/user-view/", "key": "U", "command": "alt"},
    {"page": "/branches-view/", "key": "B", "command": "alt"},
]


OPTIONAL_APP_SHORTCUTS = [
    {
        "app": "horilla.contrib.dashboard",
        "url_name": "dashboard:dashboard_list_view",
        "key": "D",
        "command": "alt",
    },
    {
        "app": "horilla.contrib.reports",
        "url_name": "reports:reports_list_view",
        "key": "R",
        "command": "alt",
    },
    {
        "app": "horilla.contrib.calendar",
        "url_name": "calendar:calendar_view",
        "key": "I",
        "command": "alt",
    },
    {
        "app": "horilla.contrib.activity",
        "page": "/activity/activity-view/",
        "key": "Y",
        "command": "alt",
    },
]


def _resolve_shortcut_page(shortcut):
    if "page" in shortcut:
        return normalize_page_url(shortcut["page"])

    try:
        return normalize_page_url(str(reverse_lazy(shortcut["url_name"])))
    except (KeyError, NoReverseMatch):
        return None


@receiver(post_migrate, dispatch_uid="keys_normalize_shortcut_pages")
def normalize_shortcut_pages_on_migrate(sender, **kwargs):
    """Normalize stored page paths so they match menu URL format."""
    if sender.name != "keys":
        return
    updated = 0
    for sk in ShortcutKey.all_objects.only("id", "page").iterator():
        normalized = normalize_page_url(sk.page)
        if normalized and normalized != sk.page:
            ShortcutKey.all_objects.filter(pk=sk.pk).update(page=normalized)
            updated += 1
    if updated:
        logger.info("Normalized %d shortcut key page URL(s)", updated)


@receiver(post_save, sender=User)
def sync_shortcut_keys_on_company_change(sender, instance, created, **kwargs):
    """
    When a user's company changes, update all their shortcut keys to the new company
    so they remain visible regardless of which active company is selected.
    """
    if created:
        return
    ShortcutKey.all_objects.filter(user=instance).update(company=instance.company)


@receiver(post_save, sender=User)
def create_all_default_shortcuts(sender, instance, created, **kwargs):
    """
    Create all default shortcut keys for a newly created user
    using a single bulk insert.
    """

    if not created:
        return

    predefined = list(DEFAULT_SHORTCUTS)
    for shortcut in OPTIONAL_APP_SHORTCUTS:
        app_name = shortcut.get("app")
        if app_name and not apps.is_installed(app_name):
            continue
        page = _resolve_shortcut_page(shortcut)
        if not page:
            continue
        predefined.append(
            {
                "page": page,
                "key": shortcut["key"],
                "command": shortcut["command"],
            }
        )

    shortcuts = [
        ShortcutKey(
            user=instance,
            page=item["page"],
            key=item["key"],
            command=item["command"],
            company=instance.company,
        )
        for item in predefined
    ]

    ShortcutKey.objects.bulk_create(shortcuts, ignore_conflicts=True)
