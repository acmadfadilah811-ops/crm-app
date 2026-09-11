"""URL configuration for the scoring_rules API."""

from rest_framework.routers import DefaultRouter

from horilla.urls import include, path
from horilla_crm.scoring_rules.api.views import (
    ScoringCriterionViewSet,
    ScoringRuleViewSet,
)

router = DefaultRouter()
router.register("scoring-rules", ScoringRuleViewSet, basename="scoringrule")
router.register(
    "scoring-criteria", ScoringCriterionViewSet, basename="scoringcriterion"
)

urlpatterns = [
    path("", include(router.urls)),
]
