"""
Merge nav view class attributes from extension specs onto a target HorillaNavView.
"""

from __future__ import annotations

from horilla.extension.nav.registry import NavExtensionSpec


def _union_sequence(*sequences) -> list:
    seen: set = set()
    result: list = []
    for seq in sequences:
        for item in seq or []:
            key = repr(item) if isinstance(item, dict) else item
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
    return result


def merge_append_attr(
    base: list | None, specs: list[NavExtensionSpec], spec_attr: str
) -> list | None:
    """Union base list with values from spec.<spec_attr> across specs."""
    additions: list = []
    for spec in specs:
        additions.extend(getattr(spec, spec_attr, None) or [])
    if not additions and not base:
        return None
    merged = _union_sequence(list(base or []), additions)
    if merged == list(base or []) and not additions:
        return None
    return merged


def merge_custom_view_type(
    base: dict | None, specs: list[NavExtensionSpec]
) -> dict | None:
    """Shallow-merge custom_view_type dicts from extension specs onto base."""
    if not specs and not base:
        return None
    merged = dict(base or {})
    changed = bool(specs)
    for spec in specs:
        updates = spec.custom_view_type_update or {}
        if updates:
            merged.update(updates)
            changed = True
    return merged if changed else None


def merge_navbar_indication_attrs(
    base: dict | None, specs: list[NavExtensionSpec]
) -> dict | None:
    """Shallow-merge navbar_indication_attrs from extension specs."""
    if not specs and not base:
        return None
    merged = dict(base or {})
    changed = bool(specs)
    for spec in specs:
        updates = spec.navbar_indication_attrs_update or {}
        if updates:
            merged.update(updates)
            changed = True
    return merged if changed else None


def merge_exclude_kanban_fields(
    base: str | None, specs: list[NavExtensionSpec]
) -> str | None:
    """Merge exclude_kanban_fields comma-separated string with extension appends."""
    parts: list[str] = []
    if base:
        parts.extend(f.strip() for f in str(base).split(",") if f.strip())
    for spec in specs:
        for name in spec.exclude_kanban_fields_append or []:
            if name and name not in parts:
                parts.append(name)
    if not parts and not base:
        return None
    merged = ",".join(parts)
    if merged == (base or ""):
        return None
    return merged


def merge_scalar_overrides(specs: list[NavExtensionSpec]) -> dict:
    """Later specs (higher priority) override earlier scalar class attributes."""
    merged: dict = {}
    for spec in specs:
        merged.update(spec.scalar_overrides)
    return merged
