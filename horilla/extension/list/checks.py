"""
Django system checks for _inherit_list extensions.
"""

from django.core.checks import Error, Tags, register
from django.views.generic import View

from horilla.extension.list.registry import LIST_EXTENSION_REGISTRY


@register(Tags.models, id="list_extensions")
def check_list_extensions(app_configs, **kwargs):
    """Validate registered list extension targets at startup."""
    errors = []
    for target_path, specs in LIST_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_list path: {target_path!r}",
                    id="list_extensions.E001",
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
                    f"Cannot import list view target {target_path!r}: {exc}",
                    id="list_extensions.E002",
                )
            )
            continue
        if not isinstance(view_cls, type) or not issubclass(view_cls, View):
            errors.append(
                Error(
                    f"{target_path!r} is not a Django View subclass",
                    id="list_extensions.E003",
                )
            )
        _ = specs
    return errors
