"""
Utilities for shortcut key page URL handling.
"""

from django.utils.encoding import force_str

from horilla.urls import NoReverseMatch, reverse_lazy
from horilla.utils.translation import gettext_lazy as _


def normalize_page_url(url):
    """
    Normalize a page path so it matches menu URLs from reverse_lazy.
    Ensures a leading slash and trailing slash (except for home "/").
    """
    if not url:
        return url
    url = str(url).strip()
    if url == "/":
        return url
    if not url.startswith("/"):
        url = f"/{url}"
    if not url.endswith("/"):
        url = f"{url}/"
    return url


def resolve_page_url(url_name):
    """Resolve a named URL to a normalized page path, or None if unavailable."""
    try:
        return normalize_page_url(str(reverse_lazy(url_name)))
    except (KeyError, NoReverseMatch):
        return None


def _menu_label(value):
    """Return a plain string label from a menu title/label value."""
    return force_str(value) if value else None


def _build_core_page_titles():
    """Known default shortcut paths (always available, no permission filter)."""
    titles = {
        "/": force_str(_("Home")),
        "/my-profile-view/": force_str(_("Profile")),
        "/user-view/": force_str(_("Users")),
        "/branches-view/": force_str(_("Branches")),
        "/regional-formating-view/": force_str(_("Regional & Formatting")),
        "/user-login-history-view/": force_str(_("Login History")),
        "/user-holiday-view/": force_str(_("Holiday")),
        "/shortkeys/short-key-view/": force_str(_("Short Keys")),
    }
    for url_name, label in (
        ("dashboard:dashboard_list_view", _("Dashboards")),
        ("reports:reports_list_view", _("Reports")),
        ("calendar:calendar_view", _("Calendar")),
    ):
        page = resolve_page_url(url_name)
        if page:
            titles[page] = force_str(label)
    activity_page = "/activity/activity-view/"
    titles[activity_page] = force_str(_("Activities"))
    return titles


def get_all_page_titles():
    """
    Build a URL -> title map from every registered menu (no permission filter).

    Rebuilt on each call so titles stay correct as apps register menus.
    """
    from horilla.menu.main_section_menu import main_section_menu
    from horilla.menu.my_settings_menu import my_settings_menu
    from horilla.menu.settings_menu import settings_registry
    from horilla.menu.sub_section_menu import sub_section_menu

    titles = _build_core_page_titles()

    for cls in my_settings_menu:
        obj = cls()
        url = normalize_page_url(getattr(obj, "url", None))
        title = _menu_label(getattr(obj, "title", None))
        if url and title:
            titles[url] = title

    for cls in settings_registry:
        obj = cls()
        for item in getattr(obj, "items", []):
            if callable(item):
                continue
            url = normalize_page_url(item.get("url"))
            label = _menu_label(item.get("label"))
            if url and label:
                titles[url] = label

    for cls in sub_section_menu:
        obj = cls()
        url = normalize_page_url(getattr(obj, "url", None))
        label = _menu_label(getattr(obj, "verbose_name", None))
        if url and label:
            titles[url] = label

    for cls in main_section_menu:
        obj = cls()
        url = normalize_page_url(getattr(obj, "url", None))
        name = _menu_label(getattr(obj, "name", None))
        if url and name:
            titles[url] = name

    return titles


def resolve_page_title(page):
    """Return display title for a stored page path."""
    normalized = normalize_page_url(page)
    if not normalized:
        return page
    return get_all_page_titles().get(normalized, page)
