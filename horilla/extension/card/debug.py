"""
Debug helpers for _inherit_card extensions.
"""

from __future__ import annotations

from horilla.extension.card.registry import get_card_extensions_for
from horilla.extension.card.resolve import _card_view_path, resolve_card_view_class


def get_card_extensions(card_view_class) -> list[str]:
    """Return dotted paths of registered extension classes for a card view."""
    path = _card_view_path(card_view_class)
    return [f"{s.module}.{s.class_name}" for s in get_card_extensions_for(path)]


def print_card_view_mro(card_view_class) -> None:
    """Print MRO for resolved card view class (stdout)."""
    resolved = resolve_card_view_class(card_view_class)
    for cls in resolved.mro():
        print(cls)
