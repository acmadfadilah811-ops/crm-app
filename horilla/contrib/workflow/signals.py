"""
Signals for the workflow app.

Listens to post_save on every model registered under the "workflow_models"
feature key and fires matching active WorkflowRules.
"""

# Standard library imports
import logging

# Third-party imports (Django)
from django.dispatch import receiver

from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.utils.middlewares import _thread_local

# First party imports (Horilla)
from horilla.db.models.signals import post_save
from horilla.registry.feature import FEATURE_REGISTRY

# Local imports
from .methods import is_running_migrations, trigger_workflow_rules
from .models import WorkflowRule

logger = logging.getLogger(__name__)


@receiver(post_save)
def trigger_workflow_rules_on_save(sender, instance, created, **kwargs):
    """
    Fire all active WorkflowRules when a registered model instance is saved.

    Only models listed in FEATURE_REGISTRY["workflow_models"] are processed so
    that every single model save in the system does not incur the overhead of a
    WorkflowRule query.

    A thread-local re-entrancy guard prevents the update_field action's own
    save() call from re-triggering workflow rules on the same instance.
    """
    if is_running_migrations():
        return

    allowed_models = FEATURE_REGISTRY.get("workflow_models", [])
    if sender not in allowed_models:
        return

    # Re-entrancy guard: skip if this save was issued by a workflow action
    executing_set = getattr(_thread_local, "_workflow_executing", set())
    instance_key = (sender, instance.pk)
    if instance_key in executing_set:
        return

    try:
        content_type = HorillaContentType.objects.get_for_model(instance)
        has_rules = WorkflowRule.objects.filter(
            model=content_type, is_active=True
        ).exists()
        if not has_rules:
            return

        trigger_type = "on_create" if created else "on_update"

        request = getattr(_thread_local, "request", None)
        user = getattr(request, "user", None) if request else None

        executing_set.add(instance_key)
        _thread_local._workflow_executing = executing_set
        try:
            trigger_workflow_rules(instance, trigger_type=trigger_type, user=user)
        finally:
            executing_set.discard(instance_key)

    except Exception as exc:
        logger.error(
            "Error in trigger_workflow_rules_on_save for %s: %s",
            sender.__name__,
            exc,
            exc_info=True,
        )
