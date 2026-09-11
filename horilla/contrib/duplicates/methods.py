"""
duplicates helper methods.
"""

# First party imports (Horilla)
from horilla.db import models
from horilla.registry.feature import FEATURE_REGISTRY

# Define your mail helper methods here


def limit_content_types():
    """
    Limit ContentType choices to only models that have
    'duplicates_includable = True'.
    """
    includable_models = []
    for model in FEATURE_REGISTRY["duplicate_models"]:
        includable_models.append(model._meta.model_name.lower())

    return models.Q(model__in=includable_models)
