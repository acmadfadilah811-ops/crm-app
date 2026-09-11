"""
Debug helpers for _inherit_nav extensions.
"""

from __future__ import annotations

from horilla.extension.nav.registry import get_nav_extensions_for
from horilla.extension.nav.resolve import _nav_view_path, resolve_nav_view_class


def get_nav_extensions(nav_view_class) -> list[str]:
    """Return dotted paths of registered extension classes for a nav view."""
    path = _nav_view_path(nav_view_class)
    return [f"{s.module}.{s.class_name}" for s in get_nav_extensions_for(path)]


def print_nav_view_mro(nav_view_class) -> None:
    """Print MRO for resolved nav view class (stdout)."""
    resolved = resolve_nav_view_class(nav_view_class)
    for cls in resolved.mro():
        print(cls)
