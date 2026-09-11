"""
URL patterns for Horilla Calendar API
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import UserAvailabilityViewSet, UserCalendarPreferenceViewSet

router = DefaultRouter()
router.register(r"user-calendar-preferences", UserCalendarPreferenceViewSet)
router.register(r"user-availabilities", UserAvailabilityViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
