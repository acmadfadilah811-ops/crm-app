"""
Opportunity stages views package.

Submodules:
  base   — stage list, navbar, create, delete, toggle-order-field, change-final
  order  — drag-and-drop order update and stage-load modal
  custom — custom stage form/save, group create, and DB initialization
"""

# Local imports
from horilla_crm.opportunities.views.opportunity_stages.base import (
    ChangeFinalStage,
    CreateOpportunityStage,
    OpportunityStageListView,
    OpportunityStageNavbar,
    OpportunityStageView,
    OpportunityStatusDeleteView,
    OpportynityToggleOrderFieldView,
)
from horilla_crm.opportunities.views.opportunity_stages.order import (
    LoadOpportunityStagesView,
    UpdateOpportunityStageOrderView,
)
from horilla_crm.opportunities.views.opportunity_stages.custom import (
    CreateOppStageGroupView,
    CustomOppStagesFormView,
    InitializeDatabaseOpportunityStages,
    SaveCustomOppStagesView,
)

__all__ = [
    # base
    "OpportunityStageView",
    "OpportunityStageNavbar",
    "OpportunityStageListView",
    "ChangeFinalStage",
    "CreateOpportunityStage",
    "OpportynityToggleOrderFieldView",
    "OpportunityStatusDeleteView",
    # order
    "UpdateOpportunityStageOrderView",
    "LoadOpportunityStagesView",
    # custom
    "CustomOppStagesFormView",
    "SaveCustomOppStagesView",
    "CreateOppStageGroupView",
    "InitializeDatabaseOpportunityStages",
]
