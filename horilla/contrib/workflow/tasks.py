"""
Celery tasks for the workflow app.

process_scheduled_workflow_executions — periodic task, queues due time triggers.
execute_workflow_time_trigger          — worker task, runs the actual action.
"""

# Standard library imports
import logging

# Third-party imports (Django)
from celery import shared_task

# First party imports (Horilla)
from horilla.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_workflow_executions():
    """
    Periodic task: find all pending ScheduledWorkflowExecution rows whose
    scheduled_at has passed and queue a worker task for each.
    """
    from .models import ScheduledWorkflowExecution

    due = ScheduledWorkflowExecution.objects.filter(
        status=ScheduledWorkflowExecution.STATUS_PENDING,
        scheduled_at__lte=timezone.now(),
    )

    count = due.count()
    logger.info("Workflow scheduler: %s executions due", count)

    for execution in due:
        execute_workflow_time_trigger.delay(execution.pk)

    return f"Queued {count} workflow time-trigger executions"


@shared_task(bind=True, max_retries=3)
def execute_workflow_time_trigger(self, execution_id):
    """
    Worker task: execute a single ScheduledWorkflowExecution.
    """
    from .methods import (
        _execute_assign_task,
        _execute_email,
        _execute_notification,
        _execute_update_field,
    )
    from .models import ScheduledWorkflowExecution

    try:
        execution = ScheduledWorkflowExecution.objects.select_related(
            "time_trigger__rule"
        ).get(pk=execution_id)
    except ScheduledWorkflowExecution.DoesNotExist:
        logger.error("ScheduledWorkflowExecution %s not found", execution_id)
        return

    if execution.status != ScheduledWorkflowExecution.STATUS_PENDING:
        return

    time_trigger = execution.time_trigger
    rule = time_trigger.rule

    try:
        model_class = rule.model.model_class()
        instance = model_class.objects.get(pk=execution.object_id)
    except Exception as exc:
        logger.error("Could not load record for execution %s: %s", execution_id, exc)
        execution.status = ScheduledWorkflowExecution.STATUS_FAILED
        execution.error_message = str(exc)
        execution.executed_at = timezone.now()
        execution.save(update_fields=["status", "error_message", "executed_at"])
        return

    user = rule.updated_by or rule.created_by

    try:
        if time_trigger.action_type == "update_field":
            _execute_update_field(time_trigger, instance, user)
        elif time_trigger.action_type == "assign_task":
            _execute_assign_task(time_trigger, instance, user)
        elif time_trigger.action_type == "email":
            _execute_email(time_trigger, instance, user)
        elif time_trigger.action_type == "notification":
            _execute_notification(time_trigger, instance, user)

        execution.status = ScheduledWorkflowExecution.STATUS_COMPLETED
        execution.executed_at = timezone.now()
        execution.save(update_fields=["status", "executed_at"])

        logger.info(
            "Workflow execution %s completed (%s on %s pk=%s)",
            execution_id,
            time_trigger.action_type,
            instance.__class__.__name__,
            instance.pk,
        )

    except Exception as exc:
        logger.error(
            "Workflow execution %s failed: %s", execution_id, exc, exc_info=True
        )
        execution.status = ScheduledWorkflowExecution.STATUS_FAILED
        execution.error_message = str(exc)
        execution.executed_at = timezone.now()
        execution.save(update_fields=["status", "error_message", "executed_at"])
        raise self.retry(exc=exc, countdown=300)
