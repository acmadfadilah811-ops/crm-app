"""Helpers for the ``custom_calendar_models`` feature registry (used by forms, not registration.py)."""

# First party imports (Horilla)
from horilla.registry.feature import FEATURE_REGISTRY


def sync_custom_calendar_models_from_dashboard_registry():
    """Mirror ``dashboard_component_models`` into ``custom_calendar_models``."""
    src = FEATURE_REGISTRY.get("dashboard_component_models", [])
    dst = FEATURE_REGISTRY.setdefault("custom_calendar_models", [])
    for model_cls in src:
        if model_cls not in dst:
            dst.append(model_cls)


def get_custom_calendar_models():
    """``[(module_key, model_cls), ...]`` — same shape as dashboard component helpers."""
    sync_custom_calendar_models_from_dashboard_registry()
    out = []
    for model_cls in FEATURE_REGISTRY.get("custom_calendar_models", []):
        out.append((model_cls.__name__.lower(), model_cls))
    return out
