"""URL configurations for the scoring_rules app."""

from horilla.urls import path
from horilla_crm.scoring_rules import views

app_name = "scoring_rules"

urlpatterns = [
    path(
        "scoring-rule-view/", views.ScoringRuleView.as_view(), name="scoring_rule_view"
    ),
    path(
        "scoring-rule-nav-view/",
        views.ScoringRuleNavbar.as_view(),
        name="scoring_rule_nav_view",
    ),
    path(
        "scoring-rule-list-view/",
        views.ScoringRuleListView.as_view(),
        name="scoring_rule_list_view",
    ),
    path(
        "scoring-rule-create-form/",
        views.ScoringRuleFormView.as_view(),
        name="scoring_rule_create_form",
    ),
    path(
        "scoring-rule-update-form/<int:pk>/",
        views.ScoringRuleFormView.as_view(),
        name="scoring_rule_update_form",
    ),
    path(
        "scoring-rule-delete-view/<int:pk>/",
        views.ScoringRuleDeleteView.as_view(),
        name="scoring_rule_delete_view",
    ),
    path(
        "scoring-rule-detail-view/<int:pk>/",
        views.ScoringRuleDetailView.as_view(),
        name="scoring_rule_detail_view",
    ),
    path(
        "scoring-rule-detail-nav-view/",
        views.ScoringRuleDetailNavbar.as_view(),
        name="scoring_rule_detail_nav_view",
    ),
    path(
        "scoring-rule-criteria-create-form/",
        views.ScoringCriterionCreateUpdateView.as_view(),
        name="scoring_rule_criteria_create_form",
    ),
    path(
        "scoring-rule-criteria-edit-form/<int:pk>/",
        views.ScoringCriterionCreateUpdateView.as_view(),
        name="scoring_rule_criteria_edit_form",
    ),
    path(
        "scoring-rule-criteria-delete/<int:pk>/",
        views.ScoringCriteriaDeleteView.as_view(),
        name="scoring_rule_criteria_delete",
    ),
    path(
        "scoring-rule-activate/<int:pk>/",
        views.ScoringActiveToggleView.as_view(),
        name="scoring_rule_activate",
    ),
]
