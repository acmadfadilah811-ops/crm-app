"""
Django system checks for _inherit_kanban extensions.
"""

from django.core.checks import Error, Tags, register

from horilla.contrib.generics.views.kanban import HorillaKanbanView
from horilla.extension.kanban.registry import KANBAN_EXTENSION_REGISTRY


@register(Tags.models, id="kanban_extensions")
def check_kanban_extensions(app_configs, **kwargs):
    """Validate registered kanban extension targets at startup."""
    errors = []
    for target_path, specs in KANBAN_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_kanban path: {target_path!r}",
                    id="kanban_extensions.E001",
                )
            )
            continue
        module_name, class_name = parts
        try:
            module = __import__(module_name, fromlist=[class_name])
            view_cls = getattr(module, class_name)
        except Exception as exc:
            errors.append(
                Error(
                    f"Cannot import kanban view target {target_path!r}: {exc}",
                    id="kanban_extensions.E002",
                )
            )
            continue
        if not isinstance(view_cls, type) or not issubclass(
            view_cls, HorillaKanbanView
        ):
            errors.append(
                Error(
                    f"{target_path!r} must be a HorillaKanbanView subclass",
                    id="kanban_extensions.E003",
                )
            )
            continue
        if view_cls is HorillaKanbanView:
            errors.append(
                Error(
                    f"{target_path!r} must be a concrete HorillaKanbanView subclass",
                    id="kanban_extensions.E004",
                )
            )
        _ = specs
    return errors
