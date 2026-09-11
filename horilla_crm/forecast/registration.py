"""
Feature registration for Forecast app.
"""

# First party imports (Horilla)
from horilla.registry.feature import register_model_for_feature

register_model_for_feature(
    app_label="forecast",
    model_name="ForecastType",
    features=["import_data", "export_data"],
)
