"""
Feature registration for Horilla duplicates app.
"""

# First party imports (Horilla)
from horilla.registry.feature import register_feature

register_feature(
    "duplicate_data",
    "duplicate_models",
    auto_register_all=False,
)
