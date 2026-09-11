"""
Registry for _inherit_card extension specs (populated at class definition time).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CARD_EXTENSION_REGISTRY: dict[str, list["CardExtensionSpec"]] = {}

CARD_COMPOSED_MAP: dict[str, type] = {}


@dataclass
class CardExtensionSpec:
    """Captured contribution from a CardExtension subclass."""

    inherit_card: str
    class_name: str
    module: str
    extension_app_label: str
    priority: int = 0
    class_attrs: dict[str, Any] = field(default_factory=dict)
    columns_insert: list[tuple[str, str | tuple]] = field(default_factory=list)
    columns_append: list[str | tuple] = field(default_factory=list)
    bulk_update_fields_append: list[str] = field(default_factory=list)
    export_exclude_append: list[str] = field(default_factory=list)
    exclude_columns_append: list[str] = field(default_factory=list)
    actions_append: list[Any] = field(default_factory=list)
    custom_bulk_actions_append: list[Any] = field(default_factory=list)
    additional_action_button_append: list[Any] = field(default_factory=list)
    exclude_quick_filter_fields_append: list[str] = field(default_factory=list)
    exclude_columns_from_sorting_append: list[str] = field(default_factory=list)
    scalar_overrides: dict[str, Any] = field(default_factory=dict)
    override_attrs: frozenset[str] = frozenset()


def register_card_extension(spec: CardExtensionSpec) -> None:
    """Append an extension spec for a target card view path."""
    CARD_EXTENSION_REGISTRY.setdefault(spec.inherit_card, []).append(spec)
    from horilla.extension.card.cache import invalidate_after_registry_change

    invalidate_after_registry_change()


def get_card_extensions_for(target_path: str) -> list[CardExtensionSpec]:
    """Return extension specs for a target, sorted by priority then registration order."""
    specs = list(CARD_EXTENSION_REGISTRY.get(target_path, []))
    specs.sort(key=lambda s: (s.priority, s.module, s.class_name))
    return specs
