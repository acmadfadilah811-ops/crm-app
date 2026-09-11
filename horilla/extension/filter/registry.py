"""
Registry for _inherit_filter extension specs (populated at class definition time).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FILTER_EXTENSION_REGISTRY: dict[str, list["FilterExtensionSpec"]] = {}

FILTER_COMPOSED_MAP: dict[str, type] = {}


@dataclass
class FilterExtensionSpec:
    """Captured contribution from a FilterExtension subclass."""

    inherit_filter: str
    class_name: str
    module: str
    extension_app_label: str
    priority: int = 0
    declared_filters: dict[str, Any] = field(default_factory=dict)
    meta_attrs: dict[str, Any] = field(default_factory=dict)
    class_attrs: dict[str, Any] = field(default_factory=dict)
    search_fields_insert: list[tuple[str, str]] = field(default_factory=list)
    search_fields_append: list[str] = field(default_factory=list)
    exclude_append: list[str] = field(default_factory=list)
    fields_append: list[str] = field(default_factory=list)
    override_filters: frozenset[str] = frozenset()


def register_filter_extension(spec: FilterExtensionSpec) -> None:
    """Append an extension spec for a target filterset path."""
    FILTER_EXTENSION_REGISTRY.setdefault(spec.inherit_filter, []).append(spec)
    from horilla.extension.filter.cache import invalidate_all

    invalidate_all()


def get_filter_extensions_for(target_path: str) -> list[FilterExtensionSpec]:
    """Return extension specs for a target, sorted by priority then registration order."""
    specs = list(FILTER_EXTENSION_REGISTRY.get(target_path, []))
    specs.sort(key=lambda s: (s.priority, s.module, s.class_name))
    return specs
