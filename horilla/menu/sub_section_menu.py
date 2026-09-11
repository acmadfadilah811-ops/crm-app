"""
Module that provides a registry for managing and retrieving sub-section in the sidebar
"""

from collections import defaultdict
from typing import Any, Dict, List, Type

from django.core.exceptions import ImproperlyConfigured

from .main_section_menu import get_main_section_menu

# Registry to hold all subsection menu classes
sub_section_menu: List[Any] = []


def register(cls: Type[Any]):
    """Decorator to register a main sub-section menu class."""
    sub_section_menu.append(cls)
    return cls


def get_sub_section_menu(request=None) -> Dict[str, List[Dict]]:
    """
    Return all registered main sub-sections grouped by section name,
    filtered by user permissions.
    """
    sections = defaultdict(list)

    main_sections = {
        section["section"]
        for section in get_main_section_menu(request=request)
        if section.get("section")
    }

    for cls in sub_section_menu:
        obj = cls()
        section_name = getattr(obj, "section", None)
        perm = getattr(obj, "perm", [])

        if isinstance(perm, str):
            perm = [perm]

        all_perms = getattr(obj, "all_perms", False)

        # Skip items if user doesn't have required perms
        if request and request.user:
            if all_perms:
                # user must have ALL permissions
                if not all(request.user.has_perm(p) for p in perm):
                    continue
            else:
                # user must have at least ONE permission
                if perm and not any(request.user.has_perm(p) for p in perm):
                    continue

        app_label = getattr(obj, "app_label", None)
        item = {
            "label": getattr(obj, "verbose_name", None),
            "icon": getattr(obj, "icon", None),
            "url": getattr(obj, "url", None),
            "class": getattr(obj, "css_class", "sidebar-link"),
            "app_label": app_label,
            "id": getattr(obj, "id", app_label),
            "perm": {
                "perms": perm,
                "all_perms": all_perms,
            },
            "position": getattr(obj, "position", None),
            "attrs": getattr(obj, "attrs", {}),
        }

        if section_name:
            if section_name not in main_sections:
                raise ImproperlyConfigured(
                    f"Sub section '{obj.__class__.__name__}' uses section "
                    f"'{section_name}' but no matching main section is registered."
                )
            sections[section_name].append(item)

    for items in sections.values():
        items.sort(key=lambda x: (x["position"] is None, x["position"]))
    return sections
