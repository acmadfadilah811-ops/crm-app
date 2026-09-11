"""
Django system checks for _inherit_card extensions.
"""

from django.core.checks import Error, Tags, register

from horilla.contrib.generics.views.card import HorillaCardView
from horilla.extension.card.registry import CARD_EXTENSION_REGISTRY


@register(Tags.models, deploy=True)
def check_card_extensions(app_configs, **kwargs):
    """Validate registered card extension targets at startup."""
    errors = []
    for target_path, _ in CARD_EXTENSION_REGISTRY.items():
        parts = target_path.rsplit(".", 1)
        if len(parts) != 2:
            errors.append(
                Error(
                    f"Invalid _inherit_card path: {target_path!r}",
                    id="card_extensions.E001",
                )
            )
            continue
        module_name, class_name = parts
        try:
            module = __import__(module_name, fromlist=[class_name])
            card_cls = getattr(module, class_name)
        except Exception as exc:
            errors.append(
                Error(
                    f"Cannot import card target {target_path!r}: {exc}",
                    id="card_extensions.E002",
                )
            )
            continue
        if not isinstance(card_cls, type) or not issubclass(card_cls, HorillaCardView):
            errors.append(
                Error(
                    f"{target_path!r} is not a HorillaCardView subclass",
                    id="card_extensions.E003",
                )
            )
        elif card_cls is HorillaCardView:
            errors.append(
                Error(
                    f"{target_path!r} must be a concrete HorillaCardView subclass",
                    id="card_extensions.E004",
                )
            )
    return errors
