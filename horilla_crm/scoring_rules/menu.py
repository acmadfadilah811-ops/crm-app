"""
Menu registration for the Horilla CRM Scoring Rules app.
"""

from horilla.contrib.core.menu import BaseSettings
from horilla.urls import reverse_lazy
from horilla_crm.scoring_rules.models import ScoringRule

BaseSettings.items.append(
    {
        "label": ScoringRule()._meta.verbose_name,
        "url": reverse_lazy("scoring_rules:scoring_rule_view"),
        "hx-target": "#settings-content",
        "hx-push-url": "true",
        "hx-select": "#scoring-rule-view",
        "hx-select-oob": "#settings-sidebar",
        "perm": "scoring_rules.view_scoringrule",
    },
)
