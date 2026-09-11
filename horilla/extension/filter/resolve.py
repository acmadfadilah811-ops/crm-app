"""
Resolve filterset classes through _inherit_filter composition.
"""

from __future__ import annotations

import django_filters

from horilla.extension.filter import cache
from horilla.extension.filter.registry import FILTER_COMPOSED_MAP


def _filter_path(filterset_class: type) -> str:
    return getattr(
        filterset_class,
        "__horilla_filter_path__",
        f"{filterset_class.__module__}.{filterset_class.__name__}",
    )


def _import_filterset_class(path: str) -> type:
    module_name, class_name = path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def clear_filter_extension_cache() -> None:
    """Clear resolver cache (tests, autoreload)."""
    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE.clear()
        FILTER_COMPOSED_MAP.clear()
    cache.reset_bootstrap_applied()


def resolve_filterset_class(
    filterset_class: type[django_filters.FilterSet] | str,
) -> type[django_filters.FilterSet]:
    """
    Return composed filterset class when extensions exist, else the original.

    Safe to call before apps are ready — returns the base class unchanged.
    """
    from horilla.extension.filter.bootstrap import apply_filter_extensions

    if isinstance(filterset_class, str):
        filterset_class = _import_filterset_class(filterset_class)

    apply_filter_extensions()

    if filterset_class in cache.RESOLVER_CACHE:
        return cache.RESOLVER_CACHE[filterset_class]

    path = _filter_path(filterset_class)
    composed = FILTER_COMPOSED_MAP.get(path)
    result = composed if composed is not None else filterset_class

    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE[filterset_class] = result
        if result is not filterset_class:
            cache.RESOLVER_CACHE[result] = result

    return result


def get_resolved_filter_path(filterset_class: type) -> str:
    """Stable path for the original target filterset (pre-composition)."""
    resolved = resolve_filterset_class(filterset_class)
    return _filter_path(resolved)
