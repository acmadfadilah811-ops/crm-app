"""
This module registers Floating, Settings, My Settings, and Main Section menus
for the approvals app
"""

# Local imports
from horilla.contrib.process import ProcessSettings
from horilla.menu import MAIN_CONTENT_HX_ATTRS, sub_section_menu

# First party imports (Horilla)
from horilla.urls import reverse_lazy
from horilla.utils.translation import gettext_lazy as _

process = ProcessSettings()
process.items.extend(
    [
        {
            "label": _("Approval Processes"),
            "url": reverse_lazy("approvals:approval_process_view"),
            "hx-target": "#settings-content",
            "hx-push-url": "true",
            "hx-select": "#approval-process-view",
            "hx-select-oob": "#settings-sidebar",
            "perm": "approvals.view_approvalrule",
            "order": 2,
        },
    ]
)


@sub_section_menu.register
class ApprovalProcessSubSection:
    """My Jobs > Approval Jobs sidebar link."""

    # Identity / placement
    section = "my_jobs"
    app_label = "approvals"
    position = 2

    # Display
    verbose_name = _("Approval Jobs")
    icon = "/assets/icons/approval.svg"

    # Behavior
    url = reverse_lazy("approvals:approval_job_view")
    attrs = MAIN_CONTENT_HX_ATTRS

    # Access control
    perm = []
