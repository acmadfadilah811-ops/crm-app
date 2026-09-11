"""List view visibility hooks for review-controlled records."""

# First party imports (Horilla)
# First party imports (Horilla)
from horilla.contrib.core.models import HorillaContentType
from horilla.contrib.generics.views.list import HorillaListView
from horilla.db.models import Exists, OuterRef
from horilla.registry.feature import FEATURE_CONFIG, FEATURE_REGISTRY

# Local party imports
# Local imports
from .models import ReviewJob


def _exclude_pending_review_records(queryset):
    """Hide records from module list views while they are under pending review."""
    model = getattr(queryset, "model", None)
    if model is None:
        return queryset

    registry_key = FEATURE_CONFIG.get("reviews", "reviews_models")
    review_models = FEATURE_REGISTRY.get(registry_key, [])
    if model not in review_models:
        return queryset

    content_type = HorillaContentType.objects.get_for_model(model)
    pending_jobs = ReviewJob.all_objects.filter(
        content_type=content_type,
        object_id=OuterRef("pk"),
        status=ReviewJob.STATUS_PENDING,
        is_active=True,
    )
    return queryset.annotate(_has_pending_review=Exists(pending_jobs)).filter(
        _has_pending_review=False
    )


def patch_horilla_list_queryset():
    """Patch HorillaListView.get_queryset once to enforce review visibility."""
    if getattr(HorillaListView, "_reviews_patched", False):
        return

    original_get_queryset = HorillaListView.get_queryset

    def wrapped_get_queryset(view_self, *args, **kwargs):
        queryset = original_get_queryset(view_self, *args, **kwargs)
        return _exclude_pending_review_records(queryset)

    HorillaListView.get_queryset = wrapped_get_queryset
    HorillaListView._reviews_patched = True
