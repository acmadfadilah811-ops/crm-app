"""
Merge kanban view class attributes from extension specs onto a target HorillaKanbanView.
"""

from __future__ import annotations

from horilla.extension.kanban.registry import KanbanExtensionSpec


def merge_exclude_kanban_fields(
    base: str | None, specs: list[KanbanExtensionSpec]
) -> str | None:
    """Append exclude_kanban_fields_append to the target CSV string."""
    parts = [p.strip() for p in (base or "").split(",") if p.strip()]
    seen = set(parts)
    changed = False

    for spec in specs:
        for field_name in spec.exclude_kanban_fields_append or []:
            name = str(field_name).strip()
            if name and name not in seen:
                seen.add(name)
                parts.append(name)
                changed = True

    if not changed and not base:
        return None
    if not parts:
        return base or ""
    return ",".join(parts)
