"""
Tests for Horilla _inherit_kanban kanban view extensions.
"""

from django.contrib.auth.models import User
from django.test import SimpleTestCase

from horilla.contrib.generics.views.kanban import HorillaKanbanView
from horilla.extension.kanban import (
    clear_kanban_extension_cache,
    resolve_kanban_view_class,
)
from horilla.extension.kanban.compose import compose_kanban_view_class
from horilla.extension.kanban.merge import merge_exclude_kanban_fields
from horilla.extension.kanban.metaclass import KanbanExtension
from horilla.extension.kanban.registry import (
    KANBAN_COMPOSED_MAP,
    KANBAN_EXTENSION_REGISTRY,
    KanbanExtensionSpec,
    register_kanban_extension,
)


class _TargetKanbanView(HorillaKanbanView):
    """Minimal HorillaKanbanView target for compose tests."""

    model = User
    columns = ["alpha", "beta"]
    exclude_kanban_fields = "alpha"
    actions = []


class _ExtKanban(KanbanExtension):
    """Sample kanban extension registered against _TargetKanbanView."""

    _inherit_kanban = "horilla.extension.kanban.tests._TargetKanbanView"
    columns_insert = [("beta", "gamma")]
    exclude_kanban_fields_append = ["gamma"]
    actions_append = [{"action": "Test"}]


class KanbanExtensionMetaclassTests(SimpleTestCase):
    """Tests for KanbanExtension registration and validation."""

    def test_invalid_inherit_kanban_raises(self):
        """Reject _inherit_kanban paths without module.Class form."""
        with self.assertRaises(ValueError):

            class _BadKanbanExt(KanbanExtension):
                """Extension with invalid _inherit_kanban path."""

                _inherit_kanban = "invalid-no-dot"

    def test_extension_class_is_registered(self):
        """Registered extensions are flagged and cannot be instantiated."""
        self.assertTrue(getattr(_ExtKanban, "_is_kanban_extension", False))
        with self.assertRaises(TypeError):
            _ExtKanban()


class KanbanExtensionMergeTests(SimpleTestCase):
    """Tests for kanban-specific merge helpers."""

    def test_merge_exclude_kanban_fields(self):
        """merge_exclude_kanban_fields joins CSV base with append list."""
        spec = KanbanExtensionSpec(
            inherit_kanban="x",
            class_name="E",
            module="m",
            extension_app_label="t",
            exclude_kanban_fields_append=["beta", "gamma"],
        )
        result = merge_exclude_kanban_fields("alpha", [spec])
        self.assertEqual(result, "alpha,beta,gamma")


class KanbanExtensionComposeTests(SimpleTestCase):
    """Tests for compose_kanban_view_class and registry updates."""

    def setUp(self):
        """Isolate registry and register a single test extension spec."""
        self._saved_registry = {
            k: list(v) for k, v in KANBAN_EXTENSION_REGISTRY.items()
        }
        clear_kanban_extension_cache()
        KANBAN_EXTENSION_REGISTRY.clear()
        KANBAN_COMPOSED_MAP.clear()
        register_kanban_extension(
            KanbanExtensionSpec(
                inherit_kanban="horilla.extension.kanban.tests._TargetKanbanView",
                class_name="_ExtKanban",
                module="horilla.extension.kanban.tests",
                extension_app_label="tests",
                columns_insert=[("beta", "gamma")],
                exclude_kanban_fields_append=["delta"],
                actions_append=[{"action": "Test"}],
                class_attrs={},
            )
        )

    def tearDown(self):
        """Restore registry and clear composed view cache."""
        clear_kanban_extension_cache()
        KANBAN_EXTENSION_REGISTRY.clear()
        KANBAN_EXTENSION_REGISTRY.update(self._saved_registry)
        KANBAN_COMPOSED_MAP.clear()
        HorillaKanbanView._view_registry.pop(User, None)

    def test_compose_mro_order(self):
        """Composed class MRO places extension mixin before target."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        mro_names = [c.__name__ for c in composed.mro()]
        self.assertEqual(mro_names[0], "_TargetKanbanViewExtended")
        self.assertIn("ExtKanbanMixin", mro_names)
        self.assertIn("_TargetKanbanView", mro_names)

    def test_columns_insert(self):
        """columns_insert appends fields after the anchor column."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertEqual(composed.columns, ["alpha", "beta", "gamma"])

    def test_exclude_kanban_fields_append(self):
        """exclude_kanban_fields_append extends the CSV exclude string."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertEqual(composed.exclude_kanban_fields, "alpha,delta")

    def test_actions_append(self):
        """actions_append adds card actions on the composed view."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertEqual(len(composed.actions), 1)

    def test_view_registry_points_to_composed(self):
        """HorillaKanbanView._view_registry maps model to composed class."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertIs(HorillaKanbanView._view_registry.get(User), composed)

    def test_composed_markers(self):
        """Composed views expose __horilla_kanban_* marker attributes."""
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertTrue(composed.__horilla_kanban_composed__)
        self.assertEqual(
            composed.__horilla_kanban_path__,
            "horilla.extension.kanban.tests._TargetKanbanView",
        )
        self.assertIs(composed.__wrapped_kanban_view__, _TargetKanbanView)

    def test_resolve_returns_composed(self):
        """resolve_kanban_view_class returns the composed subclass."""
        from horilla.extension.kanban.bootstrap import apply_kanban_extensions

        apply_kanban_extensions(force=True)
        KANBAN_COMPOSED_MAP["horilla.extension.kanban.tests._TargetKanbanView"] = (
            compose_kanban_view_class(
                "horilla.extension.kanban.tests._TargetKanbanView",
                _TargetKanbanView,
            )
        )
        resolved = resolve_kanban_view_class(_TargetKanbanView)
        self.assertIsNot(resolved, _TargetKanbanView)
        self.assertTrue(resolved.__horilla_kanban_composed__)

    def test_no_extensions_returns_target(self):
        """Empty registry returns the original target view class."""
        KANBAN_EXTENSION_REGISTRY.clear()
        composed = compose_kanban_view_class(
            "horilla.extension.kanban.tests._TargetKanbanView",
            _TargetKanbanView,
        )
        self.assertIs(composed, _TargetKanbanView)


class KanbanExtensionUserIntegrationTests(SimpleTestCase):
    """Integration tests with core UserKanbanView kanban extension."""

    _TARGET_PATH = "horilla.contrib.core.views.users.UserKanbanView"

    def setUp(self):
        """Register a User kanban extension spec for integration tests."""
        clear_kanban_extension_cache()
        KANBAN_EXTENSION_REGISTRY.clear()
        KANBAN_COMPOSED_MAP.clear()
        register_kanban_extension(
            KanbanExtensionSpec(
                inherit_kanban=self._TARGET_PATH,
                class_name="UserKanbanExtension",
                module="horilla.extension.kanban.tests",
                extension_app_label="tests",
                columns_insert=[("first_name", "time_zone")],
                class_attrs={},
            )
        )

    def tearDown(self):
        """Clear kanban extension registry after each test."""
        clear_kanban_extension_cache()
        KANBAN_EXTENSION_REGISTRY.clear()
        KANBAN_COMPOSED_MAP.clear()

    def test_user_kanban_extension_registers(self):
        """UserKanbanExtension registers against UserKanbanView path."""
        specs = KANBAN_EXTENSION_REGISTRY.get(self._TARGET_PATH, [])
        self.assertTrue(any(s.class_name == "UserKanbanExtension" for s in specs))

    def test_user_kanban_compose_includes_time_zone(self):
        """Composed UserKanbanView columns include time_zone from extension."""
        from horilla.contrib.core.views.users import UserKanbanView
        from horilla.extension.kanban.bootstrap import apply_kanban_extensions

        apply_kanban_extensions(force=True)
        resolved = resolve_kanban_view_class(UserKanbanView)
        column_keys = []
        for col in resolved.columns:
            if isinstance(col, str):
                column_keys.append(col)
            elif isinstance(col, (list, tuple)) and len(col) >= 2:
                column_keys.append(col[1])
        self.assertIn("time_zone", column_keys)
