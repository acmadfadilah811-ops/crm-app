"""
Debugging helpers for _inherit_list extensions.
"""

from __future__ import annotations

from horilla.extension.list.registry import get_list_extensions_for


def get_list_extensions(target_path: str) -> list:
    """Return extension specs registered for a target list view path."""
    return get_list_extensions_for(target_path)


def print_list_view_mro(target_path: str) -> None:
    """Print MRO of the composed list view class (stdout)."""
    from horilla.extension.list.compose import compose_list_view_class

    composed = compose_list_view_class(target_path)
    for cls in composed.mro():
        print(cls.__module__, cls.__qualname__)
