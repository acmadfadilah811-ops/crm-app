"""
Tests for the Horilla _inherit_model extension system.
"""

from django.test import SimpleTestCase

from horilla.contrib.core.models import HorillaCoreModel
from horilla.db import models
from horilla.extension.models.metaclass import ExtensionModelBase


class ExtensionMetaclassTests(SimpleTestCase):
    """Metaclass and API surface tests (no target-model injection)."""

    def test_invalid_inherit_model_format_raises(self):
        """_inherit_model must use app_label.ModelName syntax."""
        with self.assertRaises(ValueError):
            type(
                "BadExtension",
                (HorillaCoreModel,),
                {
                    "_inherit_model": "invalid-no-dot",
                    "marker": models.CharField(max_length=1),
                },
            )

    def test_extension_class_is_placeholder(self):
        """Extension classes with _inherit_model are not registered Django models."""

        class SampleExtension(HorillaCoreModel):
            """Placeholder extension; fields inject onto core.Department."""

            _inherit_model = "core.Department"
            marker = models.CharField(max_length=1, null=True)

        self.assertTrue(getattr(SampleExtension, "_is_horilla_extension", False))
        self.assertFalse(hasattr(SampleExtension, "_meta"))

    def test_metaclass_is_on_horilla_core_model(self):
        """HorillaCoreModel uses ExtensionModelBase as its metaclass."""
        self.assertIs(HorillaCoreModel.__class__, ExtensionModelBase)
