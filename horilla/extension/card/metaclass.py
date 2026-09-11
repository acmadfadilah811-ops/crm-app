"""
Registration for CardExtension subclasses (_inherit_card).
"""

from __future__ import annotations

from django.apps import apps as django_apps
from django.core.exceptions import AppRegistryNotReady

from horilla.extension.card.registry import CardExtensionSpec, register_card_extension

_SKIP_KEYS = frozenset(
    {
        "_inherit_card",
        "_inherit_card_priority",
        "override_attrs",
        "__module__",
        "__qualname__",
        "__doc__",
    }
)

_LAYOUT_KEYS = frozenset(
    {
        "columns_insert",
        "columns_append",
        "bulk_update_fields_append",
        "export_exclude_append",
        "exclude_columns_append",
        "actions_append",
        "custom_bulk_actions_append",
        "additional_action_button_append",
        "exclude_quick_filter_fields_append",
        "exclude_columns_from_sorting_append",
    }
)

_SCALAR_OVERRIDE_KEYS = frozenset(
    {
        "filterset_class",
        "default_sort_field",
        "default_sort_direction",
        "paginate_by",
        "view_id",
        "filter_url_push",
        "enable_quick_filters",
        "bulk_update_option",
        "bulk_export_option",
        "list_column_visibility",
        "owner_filtration",
        "enable_sorting",
        "bulk_select_option",
        "table_class",
        "table_width",
        "max_visible_actions",
    }
)


def _resolve_extension_app_label(module_name: str) -> str:
    if not module_name:
        return ""
    try:
        config = django_apps.get_containing_app_config(module_name)
        if config:
            return config.label
    except AppRegistryNotReady:
        pass
    return module_name.split(".")[0]


def _validate_inherit_card_path(inherit_card: str) -> None:
    parts = inherit_card.rsplit(".", 1)
    if len(parts) != 2:
        raise ValueError(
            f"_inherit_card must be '<module>.<ClassName>', got: {inherit_card!r}"
        )
    module_name, class_name = parts
    if not module_name or not class_name:
        raise ValueError(
            f"_inherit_card must be '<module>.<ClassName>', got: {inherit_card!r}"
        )


def register_card_extension_class(cls: type) -> None:
    """Capture contributions from a CardExtension subclass."""
    inherit_card = getattr(cls, "_inherit_card", None)
    if not inherit_card:
        return

    _validate_inherit_card_path(inherit_card)

    class_attrs = {
        key: value for key, value in cls.__dict__.items() if key in _LAYOUT_KEYS
    }

    methods = {
        key: value
        for key, value in cls.__dict__.items()
        if callable(value)
        and key not in _SKIP_KEYS
        and key not in _LAYOUT_KEYS
        and key not in _SCALAR_OVERRIDE_KEYS
        and not isinstance(value, (classmethod, staticmethod))
        and not key.startswith("__")
    }
    class_attrs.update(methods)

    scalar_overrides = {
        key: getattr(cls, key)
        for key in _SCALAR_OVERRIDE_KEYS
        if key in cls.__dict__ and not key.startswith("__")
    }

    spec = CardExtensionSpec(
        inherit_card=inherit_card,
        class_name=cls.__name__,
        module=cls.__module__,
        extension_app_label=_resolve_extension_app_label(cls.__module__),
        priority=int(getattr(cls, "_inherit_card_priority", 0) or 0),
        class_attrs=class_attrs,
        columns_insert=list(getattr(cls, "columns_insert", None) or []),
        columns_append=list(getattr(cls, "columns_append", None) or []),
        bulk_update_fields_append=list(
            getattr(cls, "bulk_update_fields_append", None) or []
        ),
        export_exclude_append=list(getattr(cls, "export_exclude_append", None) or []),
        exclude_columns_append=list(getattr(cls, "exclude_columns_append", None) or []),
        actions_append=list(getattr(cls, "actions_append", None) or []),
        custom_bulk_actions_append=list(
            getattr(cls, "custom_bulk_actions_append", None) or []
        ),
        additional_action_button_append=list(
            getattr(cls, "additional_action_button_append", None) or []
        ),
        exclude_quick_filter_fields_append=list(
            getattr(cls, "exclude_quick_filter_fields_append", None) or []
        ),
        exclude_columns_from_sorting_append=list(
            getattr(cls, "exclude_columns_from_sorting_append", None) or []
        ),
        scalar_overrides=scalar_overrides,
        override_attrs=frozenset(getattr(cls, "override_attrs", ()) or ()),
    )
    register_card_extension(spec)
    cls._is_card_extension = True
    _compose_registered_target(inherit_card)


def _compose_registered_target(target_path: str) -> None:
    try:
        from horilla.extension.card.bootstrap import apply_card_extensions

        apply_card_extensions()
    except Exception:
        pass


class CardExtension:
    """
    Base class for card view extensions. Subclasses must set _inherit_card.

    Do not instantiate — URL routing uses resolve_card_view_class() on the target view.
    """

    _inherit_card = None
    _inherit_card_priority = 0
    override_attrs = ()
    _is_card_extension = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if cls is CardExtension:
            return
        if getattr(cls, "_inherit_card", None):
            register_card_extension_class(cls)

    def setup_card_view_extension(self):
        """
        Optional hook after the view instance is created.

        Override to tweak per-request card state (rare). Prefer class-level
        layout hooks (columns_insert) or method overrides with super().
        """

    def __init__(self, *args, **kwargs):
        if self.__class__ is not CardExtension:
            raise TypeError(
                f"{self.__class__.__name__} is a card extension registration class; "
                "use the composed target view via URL routing instead."
            )
        super().__init__(*args, **kwargs)
