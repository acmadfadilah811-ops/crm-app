"""
Horilla _inherit_list — compose HorillaListView from extension apps.
"""

from horilla.extension.list.bootstrap import apply_list_extensions
from horilla.extension.list.debug import get_list_extensions, print_list_view_mro
from horilla.extension.list.metaclass import ListExtension
from horilla.extension.list.registry import LIST_COMPOSED_MAP, LIST_EXTENSION_REGISTRY
from horilla.extension.list.resolve import (
    clear_list_extension_cache,
    get_resolved_list_view_path,
    resolve_list_view_class,
)

__all__ = [
    "ListExtension",
    "LIST_EXTENSION_REGISTRY",
    "LIST_COMPOSED_MAP",
    "apply_list_extensions",
    "resolve_list_view_class",
    "get_resolved_list_view_path",
    "clear_list_extension_cache",
    "get_list_extensions",
    "print_list_view_mro",
]
