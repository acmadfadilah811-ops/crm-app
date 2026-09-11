"""
Shared constants for Horilla generics forms.

Kept in a leaf module with no internal imports so both
horilla.contrib.generics.forms and horilla.contrib.core.forms.helpers
can import from here without creating a circular dependency.
"""

HORILLA_FORM_EXCLUDE = [
    "company",
    "is_active",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "additional_info",
]
