"""
URL patterns for keys API
"""

# Third-party imports
from rest_framework.routers import DefaultRouter

# Third-party imports (Django)
# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import ShortcutKeyViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r"shortcut-keys", ShortcutKeyViewSet)


# The API URLs are now determined automatically by the router
urlpatterns = [
    # Include the router URLs
    path("", include(router.urls)),
]
