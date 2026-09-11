"""Aggregate view modules for the `cadences.views` package."""

from horilla.contrib.cadences.views.core import (
    CadenceView,
    CadenceNavbar,
    CadenceListView,
    CadenceFormView,
    CadenceToggleView,
    CadenceDeleteView,
)
from horilla.contrib.cadences.views.followups import (
    CadenceFollowUpCreateView,
    CadenceFollowUpDeleteView,
    CadenceFollowupDoThisValueFieldView,
)
from horilla.contrib.cadences.views.detail import CadenceDetailView
from horilla.contrib.cadences.views.record_tab import CadenceRecordTabView

from horilla.contrib.cadences.views.cadence_report import (
    CadenceReportView,
    CadenceReportTabView,
    CadenceTaskTabView,
    CadenceTaskListView,
    CadenceCallTabView,
    CadenceCallListView,
    CadenceEmailTabView,
    CadenceEmailListView,
)

__all__ = [
    "CadenceView",
    "CadenceNavbar",
    "CadenceListView",
    "CadenceFormView",
    "CadenceFollowUpCreateView",
    "CadenceFollowUpDeleteView",
    "CadenceFollowupDoThisValueFieldView",
    "CadenceToggleView",
    "CadenceDeleteView",
    "CadenceDetailView",
    "CadenceRecordTabView",
    "CadenceReportView",
    "CadenceReportTabView",
    "CadenceTaskTabView",
    "CadenceTaskListView",
    "CadenceCallTabView",
    "CadenceCallListView",
    "CadenceEmailTabView",
    "CadenceEmailListView",
]
