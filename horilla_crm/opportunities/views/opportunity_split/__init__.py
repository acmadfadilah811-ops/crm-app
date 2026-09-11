"""
Opportunity split views package.

Submodules:
  settings — split-type configuration and admin toggle views
  manage   — per-opportunity split management views
"""

# Local imports
from horilla_crm.opportunities.views.opportunity_split.settings import (
    OpportunitySplitListView,
    OpportunitySplitNavbar,
    OpportunitySplitTypeActiveToggleView,
    SplitEnabledRequiredMixin,
    SplitTypeView,
    TeamSellingRequiredMixin,
    ToggleAllowAllUsersSplitView,
    ToggleOpportunitySplitView,
)
from horilla_crm.opportunities.views.opportunity_split.manage import (
    AddSplitRowView,
    DeleteSplitRowView,
    ManageOpportunitySplit,
    OpportunitySplitTabContentView,
    OpportunitySplitTabView,
    RecalculateSplitRowView,
    RecalculateTotalsView,
    SaveOpportunitySplitsView,
)

__all__ = [
    # settings
    "TeamSellingRequiredMixin",
    "SplitEnabledRequiredMixin",
    "SplitTypeView",
    "OpportunitySplitNavbar",
    "OpportunitySplitListView",
    "ToggleOpportunitySplitView",
    "ToggleAllowAllUsersSplitView",
    "OpportunitySplitTypeActiveToggleView",
    # manage
    "ManageOpportunitySplit",
    "OpportunitySplitTabView",
    "OpportunitySplitTabContentView",
    "SaveOpportunitySplitsView",
    "AddSplitRowView",
    "DeleteSplitRowView",
    "RecalculateTotalsView",
    "RecalculateSplitRowView",
]
