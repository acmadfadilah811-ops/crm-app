"""
URL configuration for notifications API
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import NotificationViewSet

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
