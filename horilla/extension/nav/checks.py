"""
Django system checks for _inherit_nav extensions.
"""

from django.core.checks import Error, Tags, register

from horilla.contrib.generics.views.navbar import HorillaNavView
from horilla.extension.nav.registry import NAV_EXTENSION_REGISTRY


@register(Tags.models, deploy=True)
def check_nav_extensions(app_configs, **kwargs):
    """Validate registered nav extension targets at startup."""
    errors = []
    for target_path, _ in NAV_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_nav path: {target_path!r}",
                    id="nav_extensions.E001",
                )
            )
            continue
        module_name, class_name = parts
        try:
            module = __import__(module_name, fromlist=[class_name])
            nav_cls = getattr(module, class_name)
        except Exception as exc:
            errors.append(
                Error(
                    f"Cannot import nav target {target_path!r}: {exc}",
                    id="nav_extensions.E002",
                )
            )
            continue
        if not isinstance(nav_cls, type) or not issubclass(nav_cls, HorillaNavView):
            errors.append(
                Error(
                    f"{target_path!r} is not a HorillaNavView subclass",
                    id="nav_extensions.E003",
                )
            )
        elif nav_cls is HorillaNavView:
            errors.append(
                Error(
                    f"{target_path!r} must be a concrete HorillaNavView subclass",
                    id="nav_extensions.E004",
                )
            )
    return errors
