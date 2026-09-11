"""
Feature registration for the workflow app.
"""

from horilla.registry.feature import register_feature

register_feature(
    "workflow",
    "workflow_models",
    auto_register_all=True,
)
