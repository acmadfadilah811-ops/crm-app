"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the workflow app
"""

from horilla.contrib.automations.menu import AutomationSettings

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

# Define your menu registration logic here
automation = AutomationSettings
automation.items.extend(
    [
        {
            "label": _("Workflow Rules"),
            "url": reverse_lazy("workflow:workflow_rule_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#workflow-rule-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "workflow.view_workflowrule",
            "order": 3,
        },
    ]
)
