"""
Horilla _inherit_detail — compose HorillaDetailView from extension apps.
"""

from horilla.extension.detail.bootstrap import apply_detail_extensions
from horilla.extension.detail.debug import get_detail_extensions, print_detail_view_mro
from horilla.extension.detail.metaclass import DetailExtension
from horilla.extension.detail.registry import (
    DETAIL_COMPOSED_MAP,
    DETAIL_EXTENSION_REGISTRY,
)
from horilla.extension.detail.resolve import (
    clear_detail_extension_cache,
    get_resolved_detail_view_path,
    resolve_detail_view_class,
)

__all__ = [
    "DetailExtension",
    "DETAIL_EXTENSION_REGISTRY",
    "DETAIL_COMPOSED_MAP",
    "apply_detail_extensions",
    "resolve_detail_view_class",
    "get_resolved_detail_view_path",
    "clear_detail_extension_cache",
    "get_detail_extensions",
    "print_detail_view_mro",
]
