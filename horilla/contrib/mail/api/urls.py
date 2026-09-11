"""
URL patterns for mail API, consistent with core
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import (
    HorillaMailAttachmentViewSet,
    HorillaMailConfigurationViewSet,
    HorillaMailTemplateViewSet,
    HorillaMailViewSet,
)

router = DefaultRouter()
router.register(r"mail-configurations", HorillaMailConfigurationViewSet)
router.register(r"mails", HorillaMailViewSet)
router.register(r"mail-attachments", HorillaMailAttachmentViewSet)
router.register(r"mail-templates", HorillaMailTemplateViewSet)

urlpatterns = [
    path("", include(router.urls)),
]
