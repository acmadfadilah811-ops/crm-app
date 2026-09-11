"""
URL patterns for dashboard API
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import (
    ComponentCriteriaViewSet,
    DashboardComponentViewSet,
    DashboardFolderViewSet,
    DashboardViewSet,
)

router = DefaultRouter()
router.register(r"dashboard-folders", DashboardFolderViewSet)
router.register(r"dashboard", DashboardViewSet)
router.register(r"dashboard-components", DashboardComponentViewSet)
router.register(r"component-criteria", ComponentCriteriaViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
