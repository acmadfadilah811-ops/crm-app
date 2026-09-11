"""
Debugging helpers for _inherit_detail extensions.
"""

from __future__ import annotations

from horilla.extension.detail.registry import get_detail_extensions_for


def get_detail_extensions(target_path: str) -> list:
    """Return extension specs registered for a target detail view path."""
    return get_detail_extensions_for(target_path)


def print_detail_view_mro(target_path: str) -> None:
    """Print MRO of the composed detail view class (stdout)."""
    from horilla.extension.detail.compose import compose_detail_view_class

    composed = compose_detail_view_class(target_path)
    for cls in composed.mro():
        print(cls.__module__, cls.__qualname__)
