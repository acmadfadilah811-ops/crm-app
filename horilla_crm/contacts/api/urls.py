"""
URL patterns for horilla_crm.contacts API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from horilla_crm.contacts.api.views import ContactViewSet

router = DefaultRouter()
router.register(r"contacts", ContactViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
