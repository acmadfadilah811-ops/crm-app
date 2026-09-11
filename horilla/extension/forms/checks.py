"""
Django system checks for _inherit_form extensions.
"""

from django.core.checks import Error, Tags, register

from horilla.extension.forms.registry import FORM_EXTENSION_REGISTRY


@register(Tags.models)
def check_form_extensions(app_configs, **kwargs):
    """Validate registered form extension targets at startup."""
    errors = []
    for target_path, specs in FORM_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_form path: {target_path!r}",
                    id="form_extensions.E001",
                )
            )
            continue
        module_name, class_name = parts
        try:
            module = __import__(module_name, fromlist=[class_name])
            form_cls = getattr(module, class_name)
        except Exception as exc:
            errors.append(
                Error(
                    f"Cannot import form target {target_path!r}: {exc}",
                    id="form_extensions.E002",
                )
            )
            continue
        from django import forms

        if not isinstance(form_cls, type) or not issubclass(form_cls, forms.BaseForm):
            errors.append(
                Error(
                    f"{target_path!r} is not a BaseForm subclass",
                    id="form_extensions.E003",
                )
            )
        seen_fields = set()
        for spec in specs:
            for field_name in spec.declared_fields:
                if field_name in seen_fields and field_name not in spec.override_fields:
                    errors.append(
                        Error(
                            f"Duplicate declared field {field_name!r} on {target_path} "
                            f"({spec.module}.{spec.class_name})",
                            id="form_extensions.E004",
                        )
                    )
                seen_fields.add(field_name)
    return errors
