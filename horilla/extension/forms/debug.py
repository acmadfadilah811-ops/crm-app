"""
Debug helpers for _inherit_form extensions.
"""

from __future__ import annotations

from horilla.extension.forms.registry import get_extensions_for
from horilla.extension.forms.resolve import resolve_form_class


def get_form_extensions(form_class) -> list[str]:
    """Return dotted paths of registered extension classes for a form."""
    from horilla.extension.forms.resolve import _form_path

    path = _form_path(form_class)
    return [f"{s.module}.{s.class_name}" for s in get_extensions_for(path)]


def print_form_mro(form_class) -> None:
    """Print MRO for resolved form class (stdout)."""
    resolved = resolve_form_class(form_class)
    for cls in resolved.mro():
        print(cls)
