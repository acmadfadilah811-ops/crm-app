"""Uji jembatan Bintang -> CRM: endpoint POST /api/bridge/bintang-sale/
yang dipanggil server-ke-server oleh Bintang setiap POS Sale 'paid',
untuk upsert Contact + Opportunity ("Closed Won")."""
import os
from unittest import mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from horilla.contrib.core.models.user import HorillaUser
from horilla_crm.contacts.models import Contact
from horilla_crm.opportunities.models import Opportunity, OpportunityStage

URL = "/api/bridge/bintang-sale/"


class BintangBridgeAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_tanpa_api_key_dikonfigurasi_di_server_ditolak_500(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BINTANG_BRIDGE_API_KEY", None)
            response = self.client.post(URL, {"nomor_wa": "62811"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_api_key_salah_ditolak_401(self):
        with mock.patch.dict(os.environ, {"BINTANG_BRIDGE_API_KEY": "kunci-benar"}):
            response = self.client.post(
                URL, {"nomor_wa": "62811"}, format="json", HTTP_X_API_KEY="kunci-salah"
            )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BintangBridgeSaleTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.env_patch = mock.patch.dict(os.environ, {"BINTANG_BRIDGE_API_KEY": "kunci-uji"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.owner = HorillaUser.objects.create(
            username="spv.salesmarketingcreative", first_name="SPV", last_name="Marketing",
        )
        self.stage_won = OpportunityStage.objects.create(
            name="Closed Won", order=3, probability=100, stage_type="won",
        )

    def _post(self, payload):
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY="kunci-uji")

    def test_tanpa_owner_default_ditolak_500(self):
        self.owner.delete()
        response = self._post({"nomor_wa": "6281111111111", "nama": "Tanpa Owner"})
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_contact_baru_dibuat_dan_dedup_by_nomor_wa(self):
        response = self._post({"nomor_wa": "6281234567890", "nama": "Budi Santoso"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["contact_created"])

        contact = Contact.objects.get(bintang_contact_id="6281234567890")
        self.assertEqual(contact.first_name, "Budi")
        self.assertEqual(contact.last_name, "Santoso")
        self.assertEqual(contact.contact_owner_id, self.owner.id)

        # Panggilan kedua dengan nomor_wa sama -> update, bukan duplikat.
        response2 = self._post({"nomor_wa": "6281234567890", "nama": "Budi S. (updated)"})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertFalse(response2.data["contact_created"])
        self.assertEqual(Contact.objects.filter(bintang_contact_id="6281234567890").count(), 1)
        contact.refresh_from_db()
        self.assertEqual(contact.first_name, "Budi")
        self.assertEqual(contact.last_name, "S. (updated)")

    def test_negara_nama_lengkap_dinormalisasi_ke_kode_iso(self):
        # address_country adalah CountryField (varchar(2)) -- Customer
        # Bintang kirim nama lengkap ("Indonesia"), bukan kode ISO. Regresi
        # untuk StringDataRightTruncation yang sempat kejadian di produksi.
        response = self._post({
            "nomor_wa": "6281200000001", "nama": "Budi Santoso", "negara": "Indonesia",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contact = Contact.objects.get(bintang_contact_id="6281200000001")
        self.assertEqual(str(contact.address_country), "ID")

    def test_sale_bikin_opportunity_won_dan_dedup_by_bintang_sale_id(self):
        payload = {
            "nomor_wa": "6289999999999", "nama": "Citra Dewi",
            "sale": {"id": "possale:42", "nomor": "POS-0042", "total": 250000, "tanggal": "2026-09-17"},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["opportunity_created"])
        self.assertIsNotNone(response.data["opportunity_id"])

        opp = Opportunity.objects.get(bintang_sale_id="possale:42")
        self.assertEqual(opp.stage_id, self.stage_won.id)
        self.assertEqual(float(opp.amount), 250000.0)
        self.assertEqual(opp.contact_roles.count(), 1)

        # Sale ID sama dikirim lagi -> tidak boleh bikin Opportunity kedua.
        response2 = self._post(payload)
        self.assertFalse(response2.data["opportunity_created"])
        self.assertEqual(Opportunity.objects.filter(bintang_sale_id="possale:42").count(), 1)

    def test_tanpa_stage_won_opportunity_dilewati_bukan_500(self):
        # .update() (bukan .delete()) -- sengaja lewati post_delete signal
        # handle_bulk_delete milik CRM sendiri, yang punya bug tak terkait
        # (AttributeError saat instance.company None) pada objek tanpa
        # company seperti fixture ini.
        OpportunityStage.objects.filter(pk=self.stage_won.pk).update(stage_type='open')
        payload = {
            "nomor_wa": "6281212121212", "nama": "Tanpa Stage",
            "sale": {"id": "possale:99", "nomor": "POS-0099", "total": 100000},
        }
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data["opportunity_id"])
        self.assertFalse(Opportunity.objects.filter(bintang_sale_id="possale:99").exists())

    def test_nomor_wa_kosong_ditolak_400(self):
        response = self._post({"nama": "Tanpa Nomor"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
