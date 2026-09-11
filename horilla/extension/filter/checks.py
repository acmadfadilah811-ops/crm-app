"""
Django system checks for _inherit_filter extensions.
"""

import django_filters
from django.core.checks import Error, Tags, register

from horilla.extension.filter.registry import FILTER_EXTENSION_REGISTRY


@register(Tags.models, deploy=True)
def check_filter_extensions(app_configs, **kwargs):
    """Validate registered filter extension targets at startup."""
    errors = []
    for target_path, specs in FILTER_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_filter path: {target_path!r}",
                    id="filter_extensions.E001",
                )
            )
            continue
        module_name, class_name = parts
        try:
            module = __import__(module_name, fromlist=[class_name])
            filter_cls = getattr(module, class_name)
        except Exception as exc:
            errors.append(
                Error(
                    f"Cannot import filter target {target_path!r}: {exc}",
                    id="filter_extensions.E002",
                )
            )
            continue
        if not isinstance(filter_cls, type) or not issubclass(
            filter_cls, django_filters.FilterSet
        ):
            errors.append(
                Error(
                    f"{target_path!r} is not a FilterSet subclass",
                    id="filter_extensions.E003",
                )
            )
        seen_filters = set()
        for spec in specs:
            for filter_name in spec.declared_filters:
                if (
                    filter_name in seen_filters
                    and filter_name not in spec.override_filters
                ):
                    errors.append(
                        Error(
                            f"Duplicate declared filter {filter_name!r} on "
                            f"{target_path} ({spec.module}.{spec.class_name})",
                            id="filter_extensions.E004",
                        )
                    )
                seen_filters.add(filter_name)
    return errors
