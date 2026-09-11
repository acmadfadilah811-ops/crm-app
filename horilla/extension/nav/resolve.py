"""
Resolve nav view classes through _inherit_nav composition.
"""

from __future__ import annotations

from horilla.extension.nav import cache
from horilla.extension.nav.registry import NAV_COMPOSED_MAP


def _nav_view_path(view_class: type) -> str:
    return getattr(
        view_class,
        "__horilla_nav_path__",
        f"{view_class.__module__}.{view_class.__name__}",
    )


def _import_nav_view_class(path: str) -> type:
    module_name, class_name = path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def clear_nav_extension_cache() -> None:
    """Clear resolver cache (tests, autoreload)."""
    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE.clear()
        NAV_COMPOSED_MAP.clear()
    cache.reset_bootstrap_fingerprint()


def resolve_nav_view_class(view_class: type | str) -> type:
    """
    Return composed nav view class when extensions exist, else the original.

    Safe to call before apps are ready — returns the base class unchanged.
    """
    from horilla.extension.nav.bootstrap import apply_nav_extensions

    if isinstance(view_class, str):
        view_class = _import_nav_view_class(view_class)

    apply_nav_extensions()

    if view_class in cache.RESOLVER_CACHE:
        return cache.RESOLVER_CACHE[view_class]

    path = _nav_view_path(view_class)
    composed = NAV_COMPOSED_MAP.get(path)
    result = composed if composed is not None else view_class

    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE[view_class] = result
        if result is not view_class:
            cache.RESOLVER_CACHE[result] = result

    return result


def get_resolved_nav_view_path(view_class: type) -> str:
    """Stable path for the original target nav view (pre-composition)."""
    resolved = resolve_nav_view_class(view_class)
    return _nav_view_path(resolved)
