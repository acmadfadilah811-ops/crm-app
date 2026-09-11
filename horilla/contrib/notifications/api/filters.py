"""
Filters for notifications API
"""

# Third-party imports (Django)
import django_filters

# Local imports
from ..models import Notification


class NotificationFilter(django_filters.FilterSet):
    """Filter for Notification model"""

    created_at_after = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )
    created_at_before = django_filters.DateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )

    class Meta:
        """Meta class for NotificationFilter"""

        model = Notification
        fields = {
            "user": ["exact"],
            "sender": ["exact"],
            "read": ["exact"],
            "message": ["icontains"],
            "url": ["icontains"],
        }
