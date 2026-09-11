"""
Debug helpers for _inherit_filter extensions.
"""

from __future__ import annotations

from horilla.extension.filter.registry import get_filter_extensions_for
from horilla.extension.filter.resolve import _filter_path, resolve_filterset_class


def get_filter_extensions(filterset_class) -> list[str]:
    """Return dotted paths of registered extension classes for a filterset."""
    path = _filter_path(filterset_class)
    return [f"{s.module}.{s.class_name}" for s in get_filter_extensions_for(path)]


def print_filter_mro(filterset_class) -> None:
    """Print MRO for resolved filterset class (stdout)."""
    resolved = resolve_filterset_class(filterset_class)
    for cls in resolved.mro():
        print(cls)
