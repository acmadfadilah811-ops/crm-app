"""
URL patterns for horilla_crm.campaigns API
"""

# Third-party imports (other)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from horilla_crm.campaigns.api.views import CampaignViewSet

router = DefaultRouter()
router.register(r"campaigns", CampaignViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
