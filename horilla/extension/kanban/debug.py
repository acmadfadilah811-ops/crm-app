"""
Debugging helpers for _inherit_kanban extensions.
"""

from __future__ import annotations

from horilla.extension.kanban.registry import get_kanban_extensions_for


def get_kanban_extensions(target_path: str) -> list:
    """Return extension specs registered for a target kanban view path."""
    return get_kanban_extensions_for(target_path)


def print_kanban_view_mro(target_path: str) -> None:
    """Print MRO of the composed kanban view class (stdout)."""
    from horilla.extension.kanban.compose import compose_kanban_view_class

    composed = compose_kanban_view_class(target_path)
    for cls in composed.mro():
        print(cls.__module__, cls.__qualname__)
