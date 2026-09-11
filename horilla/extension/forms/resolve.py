"""
Resolve form classes through _inherit_form composition.
"""

from __future__ import annotations

from django import forms

from horilla.extension.forms import cache
from horilla.extension.forms.registry import FORM_COMPOSED_MAP


def _form_path(form_class: type[forms.Form]) -> str:
    return getattr(
        form_class,
        "__horilla_form_path__",
        f"{form_class.__module__}.{form_class.__name__}",
    )


def _import_form_class(path: str) -> type[forms.Form]:
    module_name, class_name = path.rsplit(".", 1)
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)


def clear_form_extension_cache() -> None:
    """Clear resolver cache (tests, autoreload)."""
    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE.clear()
        FORM_COMPOSED_MAP.clear()
    cache.reset_bootstrap_applied()


def resolve_form_class(form_class: type[forms.Form] | str) -> type[forms.Form]:
    """
    Return composed form class when extensions exist, else the original.

    Safe to call before apps are ready — returns the base class unchanged.
    """
    from horilla.extension.forms.bootstrap import apply_form_extensions

    if isinstance(form_class, str):
        form_class = _import_form_class(form_class)

    apply_form_extensions()

    if form_class in cache.RESOLVER_CACHE:
        return cache.RESOLVER_CACHE[form_class]

    path = _form_path(form_class)
    composed = FORM_COMPOSED_MAP.get(path)
    result = composed if composed is not None else form_class

    with cache.RESOLVER_LOCK:
        cache.RESOLVER_CACHE[form_class] = result
        if result is not form_class:
            cache.RESOLVER_CACHE[result] = result

    return result


def get_resolved_form_path(form_class: type[forms.Form]) -> str:
    """Stable path for select2 / data-form-class (original target path)."""
    resolved = resolve_form_class(form_class)
    return _form_path(resolved)
