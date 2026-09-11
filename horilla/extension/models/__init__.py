"""
Horilla _inherit_model extension system (_inherit_model on HorillaCoreModel).
"""

from horilla.extension.models.autodetect import HorillaAutodetector
from horilla.extension.models.metaclass import EXTENSION_REGISTRY, ExtensionModelBase
from horilla.extension.models.migration_ops import (
    AlterInjectedField,
    InjectField,
    RemoveInjectedField,
)
from horilla.extension.models.registry import INJECTION_MAP, lookup_injection_owner

__all__ = [
    "HorillaAutodetector",
    "ExtensionModelBase",
    "EXTENSION_REGISTRY",
    "INJECTION_MAP",
    "lookup_injection_owner",
    "InjectField",
    "AlterInjectedField",
    "RemoveInjectedField",
]
