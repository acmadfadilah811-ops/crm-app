"""
Tests for Horilla _inherit_nav nav view extensions.
"""

from django.test import SimpleTestCase

from horilla.contrib.generics.views.navbar import HorillaNavView
from horilla.extension.nav import clear_nav_extension_cache
from horilla.extension.nav.compose import compose_nav_view_class
from horilla.extension.nav.metaclass import NavExtension
from horilla.extension.nav.registry import (
    NAV_COMPOSED_MAP,
    NAV_EXTENSION_REGISTRY,
    NavExtensionSpec,
    register_nav_extension,
)


class _TargetNavView(HorillaNavView):
    """Minimal nav target for compose tests (core User navbar pattern)."""

    model_name = "User"
    model_app_label = "core"
    column_selector_exclude_fields = ["password", "last_login"]
    exclude_kanban_fields = "department"
    enable_actions = False


class _ExtNav(NavExtension):
    """Sample nav extension registered against _TargetNavView."""

    _inherit_nav = "horilla.extension.nav.tests._TargetNavView"
    actions_append = [{"action": "Extra", "attrs": "data-test=1"}]
    custom_view_type_update = {"ext_view": {"name": "Extension view"}}
    column_selector_exclude_fields_append = ["zip_code"]


class NavExtensionMetaclassTests(SimpleTestCase):
    """Tests for NavExtension registration and validation."""

    def test_invalid_inherit_nav_raises(self):
        """Reject _inherit_nav paths without module.Class form."""
        with self.assertRaises(ValueError):

            class _BadNavExt(NavExtension):
                """Extension with invalid _inherit_nav path."""

                _inherit_nav = "invalid-no-dot"

    def test_extension_class_is_registered(self):
        """Registered extensions are flagged and cannot be instantiated."""
        self.assertTrue(getattr(_ExtNav, "_is_nav_extension", False))
        with self.assertRaises(TypeError):
            _ExtNav()


class NavExtensionComposeTests(SimpleTestCase):
    """Tests for compose_nav_view_class and composed nav markers."""

    def setUp(self):
        """Isolate registry and register a single test extension spec."""
        clear_nav_extension_cache()
        NAV_EXTENSION_REGISTRY.clear()
        NAV_COMPOSED_MAP.clear()
        register_nav_extension(
            NavExtensionSpec(
                inherit_nav="horilla.extension.nav.tests._TargetNavView",
                class_name="_ExtNav",
                module="horilla.extension.nav.tests",
                extension_app_label="tests",
                actions_append=[{"action": "Extra", "attrs": "data-test=1"}],
                custom_view_type_update={"ext_view": {"name": "Extension view"}},
                column_selector_exclude_fields_append=["zip_code"],
            )
        )

    def tearDown(self):
        """Restore registry and clear composed nav cache."""
        clear_nav_extension_cache()
        NAV_EXTENSION_REGISTRY.clear()
        NAV_COMPOSED_MAP.clear()

    def test_compose_mro_order(self):
        """Composed class MRO places extension mixin before target."""
        composed = compose_nav_view_class(
            "horilla.extension.nav.tests._TargetNavView",
            _TargetNavView,
        )
        mro_names = [c.__name__ for c in composed.mro()]
        self.assertEqual(mro_names[0], "_TargetNavViewExtended")
        self.assertIn("ExtNavMixin", mro_names)
        self.assertIn("_TargetNavView", mro_names)

    def test_column_selector_exclude_merge(self):
        """column_selector_exclude_fields_append merges with the base list."""
        composed = compose_nav_view_class(
            "horilla.extension.nav.tests._TargetNavView",
            _TargetNavView,
        )
        self.assertIn("password", composed.column_selector_exclude_fields)
        self.assertIn("zip_code", composed.column_selector_exclude_fields)

    def test_composed_markers(self):
        """Composed nav views expose __horilla_* marker attributes."""
        composed = compose_nav_view_class(
            "horilla.extension.nav.tests._TargetNavView",
            _TargetNavView,
        )
        self.assertTrue(composed.__horilla_nav_composed__)
        self.assertEqual(
            composed.__horilla_nav_path__,
            "horilla.extension.nav.tests._TargetNavView",
        )

    def test_no_extensions_returns_target(self):
        """Without registered extensions, compose returns the target unchanged."""
        NAV_EXTENSION_REGISTRY.clear()
        composed = compose_nav_view_class(
            "horilla.extension.nav.tests._TargetNavView",
            _TargetNavView,
        )
        self.assertIs(composed, _TargetNavView)
