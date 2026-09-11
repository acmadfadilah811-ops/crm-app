"""
Admin registration for the workflow app
"""

# Third-party imports (Django)
from django.contrib import admin

# Local imports
from .models import (
    ScheduledWorkflowExecution,
    WorkflowAction,
    WorkflowCondition,
    WorkflowRule,
    WorkflowTimeTriggerAction,
)

# Register your workflow models here.

admin.site.register(WorkflowRule)
admin.site.register(WorkflowCondition)
admin.site.register(WorkflowAction)
admin.site.register(WorkflowTimeTriggerAction)
admin.site.register(ScheduledWorkflowExecution)
