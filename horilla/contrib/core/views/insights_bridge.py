"""GET-only aggregation endpoints for the Bintang "Dashboard Insight
Owner" feature -- Bintang calls these server-to-server to combine CRM
sales metrics with HR/its own operational data into one cross-system
dashboard (so an AI layer, built later, can correlate signals like
"leads naik tapi konversi ke penjualan rendah" instead of seeing each
system in isolation).

Auth mirrors the existing HR->CRM bridge in this same package
(hr_bridge.py): a shared-secret X-Api-Key header, constant_time_compare,
fail-closed if the env var isn't configured. A NEW key
(INSIGHTS_BRIDGE_API_KEY) is used rather than reusing HR_BRIDGE_API_KEY
-- that one is a write-oriented employee-sync key with a different trust
boundary than a read-only aggregation key (same key value as the one
configured on the HR side -- one key trusted by both destination
systems, same convention as HR_BRIDGE_API_KEY).

Registered directly in horilla/urls/project.py (not through this
project's usual per-app get_api_paths() AppConfig convention) -- same
special-case treatment as hr_bridge.py, since this is a cross-service
bridge endpoint, not part of CRM's own domain API surface.
"""

import calendar
import datetime
import os

from django.db.models import Sum
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView


class InsightsBridgeThrottle(AnonRateThrottle):
    """Loose but present -- called per dashboard load, not high traffic."""

    scope = "insights_bridge"
    rate = "60/min"


def _check_insights_api_key(request):
    """Return None if valid, or a Response (401/500) if not. Fail-closed:
    the key MUST be configured on the server, not optional. Same pattern
    as hr_bridge.py's _cek_api_key."""
    expected = os.getenv("INSIGHTS_BRIDGE_API_KEY")
    if not expected:
        return Response(
            {"error": "Insights bridge API belum dikonfigurasi di server."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    given = request.headers.get("X-Api-Key", "") or ""
    if not given or not constant_time_compare(given, expected):
        return Response(
            {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
        )
    return None


def _last_six_months(to_date):
    """(month_start, month_end) for the 6 months ending at to_date's
    month, oldest first -- same windowing convention as horilla-hr's
    insights endpoints (horilla_api/api_views/insights/views.py)."""
    base = to_date.replace(day=1)
    for i in range(5, -1, -1):
        year = base.year
        month = base.month - i
        while month <= 0:
            month += 12
            year -= 1
        month_start = datetime.date(year, month, 1)
        last_day = calendar.monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=last_day)
        yield month_start, month_end


class InsightsLeadsView(APIView):
    """GET /api/insights/crm/leads/ -- new leads per month + conversion
    rate (is_convert=True share). New aggregation -- Lead has no direct
    FK back to the Opportunity it was converted into (conversion is
    tracked only via the is_convert flag, per leads/views/
    lead_conversion.py), so a precise lead->opportunity->won funnel
    can't be joined in SQL; reporting is_convert rate honestly here
    rather than fabricating a linked funnel."""

    permission_classes = [AllowAny]
    throttle_classes = [InsightsBridgeThrottle]

    def get(self, request):
        auth_error = _check_insights_api_key(request)
        if auth_error:
            return auth_error

        from horilla_crm.leads.models import Lead

        to_date = datetime.date.today()
        months = []
        for month_start, month_end in _last_six_months(to_date):
            qs = Lead.objects.filter(
                created_at__date__gte=month_start, created_at__date__lte=month_end
            )
            total = qs.count()
            converted = qs.filter(is_convert=True).count()
            months.append(
                {
                    "month": month_start.strftime("%b %Y"),
                    "new_leads": total,
                    "converted": converted,
                    "conversion_rate": (
                        round(converted / total * 100, 1) if total > 0 else 0
                    ),
                }
            )
        return Response({"months": months})


class InsightsPipelineView(APIView):
    """GET /api/insights/crm/pipeline/ -- active pipeline value by stage.
    New aggregation. "Active" = stage_type="open" (NOT is_final -- the
    default OpportunityStage seed data leaves "Closed Lost" with
    is_final=False, so filtering on is_final alone would wrongly count
    lost deals as active; stage_type is the field this model actually
    designed for open/won/lost semantics)."""

    permission_classes = [AllowAny]
    throttle_classes = [InsightsBridgeThrottle]

    def get(self, request):
        auth_error = _check_insights_api_key(request)
        if auth_error:
            return auth_error

        from horilla_crm.opportunities.models import Opportunity

        data = (
            Opportunity.objects.filter(stage__stage_type="open")
            .values("stage__name", "stage__order")
            .annotate(total_value=Sum("amount"))
            .order_by("stage__order")
        )
        stages = [
            {
                "stage": row["stage__name"],
                "total_value": float(row["total_value"] or 0),
            }
            for row in data
        ]
        won_total = (
            Opportunity.objects.filter(stage__stage_type="won").aggregate(
                total=Sum("amount")
            )["total"]
            or 0
        )
        return Response(
            {"stages": stages, "closed_won_total_value": float(won_total)}
        )


class InsightsCampaignsView(APIView):
    """GET /api/insights/crm/campaigns/ -- active campaign count +
    average response rate. New aggregation."""

    permission_classes = [AllowAny]
    throttle_classes = [InsightsBridgeThrottle]

    def get(self, request):
        auth_error = _check_insights_api_key(request)
        if auth_error:
            return auth_error

        from horilla_crm.campaigns.models import Campaign

        active_campaigns = Campaign.objects.filter(status="in_progress")
        active_count = active_campaigns.count()

        rates = []
        for campaign in active_campaigns:
            member_count = campaign.members.count()
            if member_count > 0:
                rates.append(campaign.responses_in_campaign / member_count * 100)
        avg_response_rate = round(sum(rates) / len(rates), 1) if rates else 0

        return Response(
            {
                "active_campaign_count": active_count,
                "average_response_rate": avg_response_rate,
            }
        )
