"""
Tests for Horilla _inherit_form form extensions.
"""

from django import forms
from django.test import SimpleTestCase

from horilla.extension.forms import clear_form_extension_cache, resolve_form_class
from horilla.extension.forms.compose import compose_form_class
from horilla.extension.forms.metaclass import FormExtension
from horilla.extension.forms.registry import (
    FORM_COMPOSED_MAP,
    FORM_EXTENSION_REGISTRY,
    ExtensionSpec,
    register_extension,
)


class _TargetForm(forms.Form):
    """Minimal form target for compose tests."""

    name = forms.CharField()
    field_order = ["name"]


class _ExtForm(FormExtension):
    """Sample form extension registered against _TargetForm."""

    _inherit_form = "horilla.extension.forms.tests._TargetForm"
    field_order_insert = [("name", "extra")]
    extra = forms.CharField(required=False)

    def clean_extra(self):
        """Uppercase the optional extra field."""
        value = self.cleaned_data.get("extra")
        return (value or "").upper()


class FormExtensionMetaclassTests(SimpleTestCase):
    """Tests for FormExtension registration and validation."""

    def test_invalid_inherit_form_raises(self):
        """Reject _inherit_form paths without module.Class form."""
        with self.assertRaises(ValueError):

            class _BadFormExt(FormExtension):
                """Extension with invalid _inherit_form path."""

                _inherit_form = "invalid-no-dot"

    def test_extension_class_is_registered(self):
        """Registered extensions are flagged and cannot be instantiated."""
        self.assertTrue(getattr(_ExtForm, "_is_form_extension", False))
        with self.assertRaises(TypeError):
            _ExtForm()


class FormExtensionComposeTests(SimpleTestCase):
    """Tests for compose_form_class and composed form markers."""

    def setUp(self):
        """Isolate registry and register a single test extension spec."""
        clear_form_extension_cache()
        FORM_EXTENSION_REGISTRY.clear()
        FORM_COMPOSED_MAP.clear()
        register_extension(
            ExtensionSpec(
                inherit_form="horilla.extension.forms.tests._TargetForm",
                class_name="_ExtForm",
                module="horilla.extension.forms.tests",
                extension_app_label="tests",
                field_order_insert=[("name", "extra")],
                declared_fields={"extra": forms.CharField(required=False)},
                class_attrs={},
            )
        )

    def tearDown(self):
        """Restore registry and clear composed form cache."""
        clear_form_extension_cache()
        FORM_EXTENSION_REGISTRY.clear()
        FORM_COMPOSED_MAP.clear()

    def test_compose_mro_order(self):
        """Composed class MRO places extension mixin before target."""
        composed = compose_form_class(
            "horilla.extension.forms.tests._TargetForm",
            _TargetForm,
        )
        mro_names = [c.__name__ for c in composed.mro()]
        self.assertEqual(mro_names[0], "_TargetFormExtended")
        self.assertIn("ExtFormMixin", mro_names)
        self.assertIn("_TargetForm", mro_names)
        self.assertLess(
            mro_names.index("ExtFormMixin"),
            mro_names.index("_TargetForm"),
        )

    def test_field_order_insert(self):
        """field_order_insert places new fields after the anchor."""
        composed = compose_form_class(
            "horilla.extension.forms.tests._TargetForm",
            _TargetForm,
        )
        self.assertEqual(composed.field_order, ["name", "extra"])

    def test_composed_markers(self):
        """Composed forms expose __horilla_* marker attributes."""
        composed = compose_form_class(
            "horilla.extension.forms.tests._TargetForm",
            _TargetForm,
        )
        self.assertTrue(composed.__horilla_composed__)
        self.assertEqual(
            composed.__horilla_form_path__,
            "horilla.extension.forms.tests._TargetForm",
        )
        self.assertIs(composed.__wrapped_form__, _TargetForm)

    def test_resolve_returns_composed(self):
        """resolve_form_class returns the composed subclass."""
        from horilla.extension.forms.bootstrap import apply_form_extensions

        apply_form_extensions(force=True)
        resolved = resolve_form_class(_TargetForm)
        self.assertIsNot(resolved, _TargetForm)
        self.assertTrue(resolved.__horilla_composed__)


class FormExtensionKeepOnFormTests(SimpleTestCase):
    """Tests for Meta.keep_on_form merge on core HolidayForm."""

    def setUp(self):
        """Clear form extension registry before each test."""
        clear_form_extension_cache()
        FORM_EXTENSION_REGISTRY.clear()
        FORM_COMPOSED_MAP.clear()

    def tearDown(self):
        """Clear form extension registry after each test."""
        clear_form_extension_cache()
        FORM_EXTENSION_REGISTRY.clear()
        FORM_COMPOSED_MAP.clear()

    def test_keep_on_form_removes_company_from_exclude(self):
        """keep_on_form meta keeps company visible when removed from exclude."""
        from horilla.contrib.core.forms.base import HolidayForm

        register_extension(
            ExtensionSpec(
                inherit_form="horilla.contrib.core.forms.base.HolidayForm",
                class_name="HolidayFormExtension",
                module="horilla.extension.forms.tests",
                extension_app_label="tests",
                meta_attrs={"keep_on_form": ("company",), "exclude": ()},
                declared_fields={},
                class_attrs={},
            )
        )
        composed = compose_form_class(
            "horilla.contrib.core.forms.base.HolidayForm",
            HolidayForm,
        )
        self.assertIn("company", composed.Meta.keep_on_form)
        self.assertNotIn("company", composed.Meta.exclude)
        self.assertIn("company", composed.base_fields)
