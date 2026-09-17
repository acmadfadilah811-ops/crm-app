"""
URL configuration for horilla project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.i18n import JavaScriptCatalog

from horilla import settings
from horilla.contrib.core.views.bintang_bridge import BintangBridgeSaleView
from horilla.contrib.core.views.hr_bridge import HRBridgeCreateAccountView
from horilla.contrib.core.views.insights_bridge import (
    InsightsCampaignsView,
    InsightsLeadsView,
    InsightsPipelineView,
)


def health_check(request):
    """Return JSON ``{"status": "ok"}`` for load balancer or uptime probes."""
    return JsonResponse({"status": "ok"}, status=200)


urlpatterns = [
    path("health/", health_check),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("jsi18n/", JavaScriptCatalog.as_view(), name="javascript-catalog"),
    path("summernote/", include("django_summernote.urls")),
    path("api/", include("horilla.api_urls")),

    # Jembatan HR (Horilla HR) -> CRM: auto-provision akun tim marketing
    # saat HR buat karyawan baru/approve rekrutmen (lihat
    # horilla/contrib/core/views/hr_bridge.py).
    path("api/bridge/hr-employee/", HRBridgeCreateAccountView.as_view(), name="hr-bridge-create-account"),

    # Jembatan Bintang -> CRM: auto-sync Contact + Opportunity ("won")
    # saat POS Sale berstatus 'paid' (lihat
    # horilla/contrib/core/views/bintang_bridge.py).
    path("api/bridge/bintang-sale/", BintangBridgeSaleView.as_view(), name="bintang-bridge-sale"),

    # Dashboard Insight Owner (Bintang): agregasi baca-saja lintas
    # sistem, auth sama seperti bridge HR->CRM di atas (lihat
    # horilla/contrib/core/views/insights_bridge.py).
    path("api/insights/crm/leads/", InsightsLeadsView.as_view(), name="insights-crm-leads"),
    path("api/insights/crm/pipeline/", InsightsPipelineView.as_view(), name="insights-crm-pipeline"),
    path("api/insights/crm/campaigns/", InsightsCampaignsView.as_view(), name="insights-crm-campaigns"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# After all AppConfig.ready() hooks (extension apps may load after CRM).
from horilla.extension.bootstrap import bootstrap_extensions

bootstrap_extensions()
