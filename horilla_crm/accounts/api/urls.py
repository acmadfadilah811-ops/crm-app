"""
URL patterns for horilla_crm.accounts API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from horilla_crm.accounts.api.views import (
    AccountViewSet,
    PartnerAccountRelationshipViewSet,
)

router = DefaultRouter()
router.register(r"accounts", AccountViewSet)
router.register(r"partner-account-relationships", PartnerAccountRelationshipViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
