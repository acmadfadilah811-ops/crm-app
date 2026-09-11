"""
Tests for Horilla _inherit_detail detail view extensions.
"""

from django.contrib.auth.models import User
from django.test import SimpleTestCase

from horilla.contrib.generics.views.details import HorillaDetailView
from horilla.extension.detail import (
    clear_detail_extension_cache,
    resolve_detail_view_class,
)
from horilla.extension.detail.compose import compose_detail_view_class
from horilla.extension.detail.metaclass import DetailExtension
from horilla.extension.detail.registry import (
    DETAIL_COMPOSED_MAP,
    DETAIL_EXTENSION_REGISTRY,
    DetailExtensionSpec,
    register_detail_extension,
)


class _TargetDetailView(HorillaDetailView):
    """Minimal HorillaDetailView target for compose tests."""

    model = User
    body = ["alpha", "beta"]
    excluded_fields = ["gamma"]
    actions = []


class _ExtDetail(DetailExtension):
    """Sample detail extension registered against _TargetDetailView."""

    _inherit_detail = "horilla.extension.detail.tests._TargetDetailView"
    body_insert = [("beta", "delta")]
    excluded_fields_append = ["epsilon"]
    actions_append = [{"action": "Test"}]


class DetailExtensionMetaclassTests(SimpleTestCase):
    """Tests for DetailExtension registration and validation."""

    def test_invalid_inherit_detail_raises(self):
        """Reject _inherit_detail paths without module.Class form."""
        with self.assertRaises(ValueError):

            class _BadDetailExt(DetailExtension):
                """Extension with invalid _inherit_detail path."""

                _inherit_detail = "invalid-no-dot"

    def test_extension_class_is_registered(self):
        """Registered extensions are flagged and cannot be instantiated."""
        self.assertTrue(getattr(_ExtDetail, "_is_detail_extension", False))
        with self.assertRaises(TypeError):
            _ExtDetail()


class DetailExtensionComposeTests(SimpleTestCase):
    """Tests for compose_detail_view_class and registry updates."""

    def setUp(self):
        """Isolate registry and register a single test extension spec."""
        self._saved_registry = {
            k: list(v) for k, v in DETAIL_EXTENSION_REGISTRY.items()
        }
        clear_detail_extension_cache()
        DETAIL_EXTENSION_REGISTRY.clear()
        DETAIL_COMPOSED_MAP.clear()
        register_detail_extension(
            DetailExtensionSpec(
                inherit_detail="horilla.extension.detail.tests._TargetDetailView",
                class_name="_ExtDetail",
                module="horilla.extension.detail.tests",
                extension_app_label="tests",
                body_insert=[("beta", "delta")],
                excluded_fields_append=["epsilon"],
                actions_append=[{"action": "Test"}],
                class_attrs={},
            )
        )

    def tearDown(self):
        """Restore registry and clear composed view cache."""
        clear_detail_extension_cache()
        DETAIL_EXTENSION_REGISTRY.clear()
        DETAIL_EXTENSION_REGISTRY.update(self._saved_registry)
        DETAIL_COMPOSED_MAP.clear()
        HorillaDetailView._view_registry.pop(User, None)

    def test_compose_mro_order(self):
        """Composed class MRO places extension mixin before target."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        mro_names = [c.__name__ for c in composed.mro()]
        self.assertEqual(mro_names[0], "_TargetDetailViewExtended")
        self.assertIn("ExtDetailMixin", mro_names)
        self.assertIn("_TargetDetailView", mro_names)

    def test_body_insert(self):
        """body_insert appends fields after the anchor column."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertEqual(composed.body, ["alpha", "beta", "delta"])

    def test_excluded_fields_append(self):
        """excluded_fields_append unions with target excluded_fields."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertIn("gamma", composed.excluded_fields)
        self.assertIn("epsilon", composed.excluded_fields)

    def test_actions_append(self):
        """actions_append adds header actions on the composed view."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertEqual(len(composed.actions), 1)

    def test_view_registry_points_to_composed(self):
        """HorillaDetailView._view_registry maps model to composed class."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertIs(HorillaDetailView._view_registry.get(User), composed)

    def test_composed_markers(self):
        """Composed views expose __horilla_detail_* marker attributes."""
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertTrue(composed.__horilla_detail_composed__)
        self.assertEqual(
            composed.__horilla_detail_path__,
            "horilla.extension.detail.tests._TargetDetailView",
        )
        self.assertIs(composed.__wrapped_detail_view__, _TargetDetailView)

    def test_resolve_returns_composed(self):
        """resolve_detail_view_class returns the composed subclass."""
        from horilla.extension.detail.bootstrap import apply_detail_extensions

        apply_detail_extensions(force=True)
        DETAIL_COMPOSED_MAP["horilla.extension.detail.tests._TargetDetailView"] = (
            compose_detail_view_class(
                "horilla.extension.detail.tests._TargetDetailView",
                _TargetDetailView,
            )
        )
        resolved = resolve_detail_view_class(_TargetDetailView)
        self.assertIsNot(resolved, _TargetDetailView)
        self.assertTrue(resolved.__horilla_detail_composed__)

    def test_no_extensions_returns_target(self):
        """Empty registry returns the original target view class."""
        DETAIL_EXTENSION_REGISTRY.clear()
        composed = compose_detail_view_class(
            "horilla.extension.detail.tests._TargetDetailView",
            _TargetDetailView,
        )
        self.assertIs(composed, _TargetDetailView)


class DetailExtensionUserIntegrationTests(SimpleTestCase):
    """Integration tests with core UserDetailView detail extension."""

    _TARGET_PATH = "horilla.contrib.core.views.users.UserDetailView"

    def setUp(self):
        """Register a User detail extension spec for integration tests."""
        clear_detail_extension_cache()
        DETAIL_EXTENSION_REGISTRY.clear()
        DETAIL_COMPOSED_MAP.clear()
        register_detail_extension(
            DetailExtensionSpec(
                inherit_detail=self._TARGET_PATH,
                class_name="UserDetailExtension",
                module="horilla.extension.detail.tests",
                extension_app_label="tests",
                body_append=["time_zone"],
                class_attrs={},
            )
        )

    def tearDown(self):
        """Clear detail extension registry after each test."""
        clear_detail_extension_cache()
        DETAIL_EXTENSION_REGISTRY.clear()
        DETAIL_COMPOSED_MAP.clear()

    def test_user_detail_extension_registers(self):
        """UserDetailExtension registers against UserDetailView path."""
        specs = DETAIL_EXTENSION_REGISTRY.get(self._TARGET_PATH, [])
        self.assertTrue(any(s.class_name == "UserDetailExtension" for s in specs))

    def test_user_detail_compose_includes_time_zone(self):
        """Composed UserDetailView body includes time_zone from extension."""
        from horilla.contrib.core.views.users import UserDetailView
        from horilla.extension.detail.bootstrap import apply_detail_extensions

        apply_detail_extensions(force=True)
        resolved = resolve_detail_view_class(UserDetailView)
        self.assertIn("time_zone", resolved.body)
