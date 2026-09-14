"""Uji 3 endpoint agregasi /api/insights/crm/... -- dipanggil server-to-
server oleh Bintang (Dashboard Insight Owner), BUKAN oleh user CRM
biasa. Auth-nya shared-secret X-Api-Key (mirror pola bridge HR->CRM
yang sudah ada di horilla/contrib/core/views/hr_bridge.py), bukan
session/JWT user."""

from unittest import mock

from django.test import TestCase

from horilla.contrib.core.models.user import HorillaUser


def _make_owner(username):
    return HorillaUser.objects.create(
        username=username, email=f"{username}@test.horilla"
    )


class InsightsCRMAuthTests(TestCase):
    """Auth berlaku sama di ketiga endpoint -- cukup diuji sekali lewat
    salah satunya (leads), bukan diulang 3x."""

    @mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
    def test_tanpa_api_key_ditolak_401(self):
        response = self.client.get("/api/insights/crm/leads/")
        self.assertEqual(response.status_code, 401)

    @mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
    def test_api_key_salah_ditolak_401(self):
        response = self.client.get(
            "/api/insights/crm/leads/", HTTP_X_API_KEY="kunci-salah"
        )
        self.assertEqual(response.status_code, 401)

    @mock.patch.dict("os.environ", {}, clear=True)
    def test_fail_closed_kalau_env_var_kosong(self):
        response = self.client.get(
            "/api/insights/crm/leads/", HTTP_X_API_KEY="apa-saja"
        )
        self.assertEqual(response.status_code, 500)

    @mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
    def test_api_key_benar_diterima(self):
        response = self.client.get(
            "/api/insights/crm/leads/", HTTP_X_API_KEY="kunci-benar"
        )
        self.assertEqual(response.status_code, 200)


@mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
class InsightsCRMDataTests(TestCase):
    def setUp(self):
        self.headers = {"HTTP_X_API_KEY": "kunci-benar"}

    def _get(self, path):
        return self.client.get(path, **self.headers)

    def test_leads_conversion_rate(self):
        from horilla_crm.leads.models import Lead, LeadStatus

        owner = _make_owner("lead.owner")
        status_obj, _ = LeadStatus.objects.get_or_create(
            name="Uji Status", defaults={"probability": 50}
        )

        def _make_lead(email, is_convert):
            return Lead.objects.create(
                first_name="Uji",
                last_name="Lead",
                lead_owner=owner,
                email=email,
                lead_source="website",
                lead_status=status_obj,
                lead_company="PT Uji",
                industry="other",
                country="ID",
                is_convert=is_convert,
            )

        _make_lead("lead1@test.horilla", True)
        _make_lead("lead2@test.horilla", False)

        response = self._get("/api/insights/crm/leads/")
        self.assertEqual(response.status_code, 200)
        months = response.data["months"]
        self.assertEqual(len(months), 6)
        current_month = months[-1]
        self.assertEqual(current_month["new_leads"], 2)
        self.assertEqual(current_month["converted"], 1)
        self.assertEqual(current_month["conversion_rate"], 50.0)

    def test_pipeline_value_per_stage_hanya_yang_open(self):
        from horilla_crm.opportunities.models import Opportunity, OpportunityStage

        owner = _make_owner("opp.owner")
        open_stage, _ = OpportunityStage.objects.get_or_create(
            name="Uji Open",
            defaults={"order": 1, "stage_type": "open", "probability": 30},
        )
        won_stage, _ = OpportunityStage.objects.get_or_create(
            name="Uji Won",
            defaults={"order": 2, "stage_type": "won", "probability": 100},
        )
        lost_stage, _ = OpportunityStage.objects.get_or_create(
            name="Uji Lost",
            defaults={"order": 3, "stage_type": "lost", "probability": 0},
        )
        Opportunity.objects.create(
            name="Deal Open", stage=open_stage, owner=owner, amount=1000000
        )
        Opportunity.objects.create(
            name="Deal Won", stage=won_stage, owner=owner, amount=5000000
        )
        Opportunity.objects.create(
            name="Deal Lost", stage=lost_stage, owner=owner, amount=9999999
        )

        response = self._get("/api/insights/crm/pipeline/")
        self.assertEqual(response.status_code, 200)
        stage_names = [s["stage"] for s in response.data["stages"]]
        self.assertIn("Uji Open", stage_names)
        self.assertNotIn("Uji Won", stage_names)
        self.assertNotIn("Uji Lost", stage_names)
        self.assertEqual(response.data["closed_won_total_value"], 5000000.0)

    def test_campaign_active_count_dan_response_rate(self):
        from horilla_crm.campaigns.models import Campaign, CampaignMember

        owner = _make_owner("camp.owner")
        active = Campaign.objects.create(
            campaign_name="Kampanye Aktif",
            campaign_owner=owner,
            status="in_progress",
            campaign_type="email",
            expected_response=0,
        )
        Campaign.objects.create(
            campaign_name="Kampanye Selesai",
            campaign_owner=owner,
            status="completed",
            campaign_type="email",
            expected_response=0,
        )
        CampaignMember.objects.create(campaign=active, member_status="responded")
        CampaignMember.objects.create(campaign=active, member_status="sent")

        response = self._get("/api/insights/crm/campaigns/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["active_campaign_count"], 1)
        self.assertEqual(response.data["average_response_rate"], 50.0)
