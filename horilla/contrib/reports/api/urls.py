"""
URL patterns for horilla.contrib.reports API

This module mirrors the URL structure of other app APIs
using DefaultRouter for consistent endpoint patterns.
"""

# Third-party imports (Django)
from rest_framework.routers import DefaultRouter

# First party imports (Horilla)
from horilla.urls import include, path

# Local imports
from .views import ReportFolderViewSet, ReportViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r"reports", ReportViewSet, basename="report")
router.register(r"report-folders", ReportFolderViewSet, basename="reportfolder")

urlpatterns = [
    path("", include(router.urls)),
]
