"""Views for the scoring_rules app."""

from horilla_crm.scoring_rules.views.scoring_rule import (
    ScoringRuleView,
    ScoringRuleNavbar,
    ScoringRuleListView,
    ScoringRuleFormView,
    ScoringRuleDeleteView,
    ScoringRuleDetailView,
    ScoringRuleDetailNavbar,
    ScoringCriterionCreateUpdateView,
    ScoringCriteriaDeleteView,
    ScoringActiveToggleView,
)

__all__ = [
    "ScoringRuleView",
    "ScoringRuleNavbar",
    "ScoringRuleListView",
    "ScoringRuleFormView",
    "ScoringRuleDeleteView",
    "ScoringRuleDetailView",
    "ScoringRuleDetailNavbar",
    "ScoringCriterionCreateUpdateView",
    "ScoringCriteriaDeleteView",
    "ScoringActiveToggleView",
]
