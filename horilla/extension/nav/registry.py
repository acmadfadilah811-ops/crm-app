"""
Registry for _inherit_nav extension specs (populated at class definition time).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

NAV_EXTENSION_REGISTRY: dict[str, list["NavExtensionSpec"]] = {}

NAV_COMPOSED_MAP: dict[str, type] = {}


@dataclass
class NavExtensionSpec:
    """Captured contribution from a NavExtension subclass."""

    inherit_nav: str
    class_name: str
    module: str
    extension_app_label: str
    priority: int = 0
    class_attrs: dict[str, Any] = field(default_factory=dict)
    actions_append: list[Any] = field(default_factory=list)
    custom_view_type_update: dict[str, Any] = field(default_factory=dict)
    column_selector_exclude_fields_append: list[str] = field(default_factory=list)
    exclude_kanban_fields_append: list[str] = field(default_factory=list)
    navbar_indication_attrs_update: dict[str, Any] = field(default_factory=dict)
    scalar_overrides: dict[str, Any] = field(default_factory=dict)
    override_attrs: frozenset[str] = frozenset()


def register_nav_extension(spec: NavExtensionSpec) -> None:
    """Append an extension spec for a target nav view path."""
    NAV_EXTENSION_REGISTRY.setdefault(spec.inherit_nav, []).append(spec)
    from horilla.extension.nav.cache import invalidate_after_registry_change

    invalidate_after_registry_change()


def get_nav_extensions_for(target_path: str) -> list[NavExtensionSpec]:
    """Return extension specs for a target, sorted by priority then registration order."""
    specs = list(NAV_EXTENSION_REGISTRY.get(target_path, []))
    specs.sort(key=lambda s: (s.priority, s.module, s.class_name))
    return specs
