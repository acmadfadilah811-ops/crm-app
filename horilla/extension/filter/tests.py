"""
Tests for Horilla _inherit_filter filterset extensions.
"""

import django_filters
from django.test import SimpleTestCase

from horilla.extension.filter import (
    clear_filter_extension_cache,
    resolve_filterset_class,
)
from horilla.extension.filter.compose import compose_filterset_class
from horilla.extension.filter.metaclass import FilterExtension
from horilla.extension.filter.registry import (
    FILTER_COMPOSED_MAP,
    FILTER_EXTENSION_REGISTRY,
    FilterExtensionSpec,
    register_filter_extension,
)


class _TargetFilter(django_filters.FilterSet):
    """Minimal filterset target for compose tests."""

    name = django_filters.CharFilter(field_name="name", lookup_expr="icontains")

    class Meta:
        """FilterSet meta for _TargetFilter."""

        fields = ["name"]
        search_fields = ["name"]


class _ExtFilter(FilterExtension):
    """Sample filter extension registered against _TargetFilter."""

    _inherit_filter = "horilla.extension.filter.tests._TargetFilter"
    search_fields_append = ["extra_search"]


class FilterExtensionMetaclassTests(SimpleTestCase):
    """Tests for FilterExtension registration and validation."""

    def test_invalid_inherit_filter_raises(self):
        """Reject _inherit_filter paths without module.Class form."""
        with self.assertRaises(ValueError):

            class _BadFilterExt(FilterExtension):
                """Extension with invalid _inherit_filter path."""

                _inherit_filter = "invalid-no-dot"

    def test_extension_class_is_registered(self):
        """Registered extensions are flagged and cannot be instantiated."""
        self.assertTrue(getattr(_ExtFilter, "_is_filter_extension", False))
        with self.assertRaises(TypeError):
            _ExtFilter()


class FilterExtensionComposeTests(SimpleTestCase):
    """Tests for compose_filterset_class and composed filterset markers."""

    def setUp(self):
        """Isolate registry and register a single test extension spec."""
        clear_filter_extension_cache()
        FILTER_EXTENSION_REGISTRY.clear()
        FILTER_COMPOSED_MAP.clear()
        register_filter_extension(
            FilterExtensionSpec(
                inherit_filter="horilla.extension.filter.tests._TargetFilter",
                class_name="_ExtFilter",
                module="horilla.extension.filter.tests",
                extension_app_label="tests",
                search_fields_append=["extra_search"],
            )
        )

    def tearDown(self):
        """Restore registry and clear composed filterset cache."""
        clear_filter_extension_cache()
        FILTER_EXTENSION_REGISTRY.clear()
        FILTER_COMPOSED_MAP.clear()

    def test_compose_mro_order(self):
        """Composed class MRO places extension mixin before target."""
        composed = compose_filterset_class(
            "horilla.extension.filter.tests._TargetFilter",
            _TargetFilter,
        )
        mro_names = [c.__name__ for c in composed.mro()]
        self.assertEqual(mro_names[0], "_TargetFilterExtended")
        self.assertIn("ExtFilterMixin", mro_names)
        self.assertIn("_TargetFilter", mro_names)

    def test_search_fields_append(self):
        """search_fields_append adds fields after the base Meta.search_fields."""
        composed = compose_filterset_class(
            "horilla.extension.filter.tests._TargetFilter",
            _TargetFilter,
        )
        self.assertEqual(
            list(composed.Meta.search_fields),
            ["name", "extra_search"],
        )

    def test_composed_markers(self):
        """Composed filtersets expose __horilla_* marker attributes."""
        composed = compose_filterset_class(
            "horilla.extension.filter.tests._TargetFilter",
            _TargetFilter,
        )
        self.assertTrue(composed.__horilla_composed__)
        self.assertEqual(
            composed.__horilla_filter_path__,
            "horilla.extension.filter.tests._TargetFilter",
        )

    def test_resolve_returns_composed(self):
        """resolve_filterset_class returns the composed subclass."""
        from horilla.extension.filter.bootstrap import apply_filter_extensions

        apply_filter_extensions(force=True)
        FILTER_COMPOSED_MAP["horilla.extension.filter.tests._TargetFilter"] = (
            compose_filterset_class(
                "horilla.extension.filter.tests._TargetFilter",
                _TargetFilter,
            )
        )
        resolved = resolve_filterset_class(_TargetFilter)
        self.assertNotEqual(resolved, _TargetFilter)
        self.assertTrue(resolved.__horilla_composed__)

    def test_no_extensions_returns_target(self):
        """Without registered extensions, compose returns the target unchanged."""
        FILTER_EXTENSION_REGISTRY.clear()
        composed = compose_filterset_class(
            "horilla.extension.filter.tests._TargetFilter",
            _TargetFilter,
        )
        self.assertIs(composed, _TargetFilter)
