"""Migrasi 0011 peluang: hapus salinan kolom bawaan lama, jangan sentuh kolom yang disesuaikan pengguna."""
import importlib

from django.apps import apps
from django.test import TestCase

from horilla.contrib.core.models import ListColumnVisibility
from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.user import HorillaUser

URL_NAME = "crm_opportunities_opportunities-view"
BAWAAN_LAMA = [
    ["Opportunity Name", "name"], ["Amount", "amount"], ["Close Date", "close_date"],
    ["Stage", "stage"], ["Type", "opportunity_type"], ["Primary Campaign Source", "primary_campaign_source"],
]


class ResetKolomPeluangTests(TestCase):
    def setUp(self):
        company = Company.objects.create(name="Star", email="info@contoh.com")
        self.lama = HorillaUser.objects.create(username="pengguna.lama", company=company)
        self.kustom = HorillaUser.objects.create(username="pengguna.kustom", company=company)

    def _simpan(self, user, kolom, model_name="Opportunity", url_name=URL_NAME):
        return ListColumnVisibility.all_objects.create(
            user=user, model_name=model_name, app_label="opportunities", url_name=url_name,
            context="", visible_fields=kolom,
        )

    def _jalankan(self):
        modul = importlib.import_module("horilla_crm.opportunities.migrations.0011_reset_kolom_default_peluang")
        modul.hapus_salinan_bawaan_lama(apps, None)

    def test_hanya_salinan_bawaan_lama_yang_dihapus(self):
        self._simpan(self.lama, BAWAAN_LAMA)
        kustom = self._simpan(self.kustom, BAWAAN_LAMA + [["Company", "company"]])
        tahap = self._simpan(self.lama, [["Stage Name", "name"]], model_name="OpportunityStage", url_name="")
        lain_url = self._simpan(self.kustom, BAWAAN_LAMA, url_name="crm_campaigns_campaign-detail-view")

        self._jalankan()

        sisa = set(ListColumnVisibility.all_objects.values_list("pk", flat=True))
        self.assertEqual(sisa, {kustom.pk, tahap.pk, lain_url.pk})

    def test_tanpa_data_tidak_error(self):
        self._jalankan()
        self.assertEqual(ListColumnVisibility.all_objects.count(), 0)
