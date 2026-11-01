"""Uji jembatan Bintang -> CRM: endpoint POST /api/bridge/bintang-sale/
yang dipanggil server-ke-server oleh Bintang setiap POS Sale 'paid',
untuk upsert Contact + Opportunity ("Closed Won")."""
import os
from unittest import mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from horilla.contrib.core.models.base import Company
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
        self.company = Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com")
        self.owner = HorillaUser.objects.create(
            username="spv.salesmarketingcreative", first_name="SPV", last_name="Marketing",
            company=self.company,
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
        # Tanpa ini, Contact ADA di database tapi TIDAK KELIHATAN di UI CRM
        # (CompanyFilteredManager filter by company sesi browser) -- bug
        # nyata yang ditemukan user lewat audit data dummy.
        self.assertEqual(contact.company_id, self.company.id)

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

    def test_sale_total_float_tidak_crash_expected_revenue(self):
        # Opportunity.save() menghitung expected_revenue = amount *
        # (probability/100), probability Decimal -- payload JSON dari
        # Bintang kirim total sebagai float (mis. 7500.0), yang sempat
        # bikin TypeError (float * Decimal) di produksi.
        response = self._post({
            "nomor_wa": "6281200000055", "nama": "Total Float",
            "sale": {"id": "possale:float-total", "nomor": "POS-0055", "total": 7500.0, "tanggal": "2026-09-17"},
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["opportunity_created"])
        opp = Opportunity.objects.get(bintang_sale_id="possale:float-total")
        self.assertEqual(float(opp.amount), 7500.0)

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
        self.assertEqual(opp.company_id, self.company.id)

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


class BintangBridgeOrderKasirTests(BintangBridgeSaleTests):
    """Order kasir (StarFoto/Advertising) dikirim dari Bintang (2026-10-12): Open saat
    belum lunas, Closed Won saat lunas; pemilik = penjual bila punya akun CRM."""

    def setUp(self):
        super().setUp()
        self.stage_open = OpportunityStage.objects.create(
            name="Negotiation", order=1, probability=50, stage_type="open",
        )
        self.staff = HorillaUser.objects.create(
            username="sales.uji", first_name="Sales", last_name="Uji", company=self.company, hr_employee_id=44,
        )

    def _kirim(self, lunas, total=200000, penjual=None, sale_id="POS-ORD-ABC123"):
        payload = {
            "nomor_wa": "6281300000001", "nama": "Dinda Foto",
            "sale": {"id": sale_id, "nomor": sale_id, "total": total, "tanggal": "2026-10-12",
                     "lunas": lunas, "unit_bisnis": "StarFoto"},
        }
        if penjual is not None:
            payload["penjual_hr_employee_id"] = penjual
        return self._post(payload)

    def test_belum_lunas_open_lalu_lunas_jadi_won_tanpa_duplikat(self):
        r = self._kirim(False, total=100000)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        opp = Opportunity.objects.get(bintang_sale_id="POS-ORD-ABC123")
        self.assertEqual(opp.stage_id, self.stage_open.id)
        self.assertEqual(opp.name, "Penjualan StarFoto POS-ORD-ABC123")

        # Total naik (usulan tambahan dikonfirmasi) selama masih Open: amount ikut.
        self._kirim(False, total=150000)
        opp.refresh_from_db()
        self.assertEqual(float(opp.amount), 150000.0)
        self.assertEqual(opp.stage_id, self.stage_open.id)

        # Lunas -> Closed Won, tetap satu Opportunity.
        r = self._kirim(True, total=150000)
        self.assertFalse(r.data["opportunity_created"])
        opp.refresh_from_db()
        self.assertEqual(opp.stage_id, self.stage_won.id)
        self.assertEqual(Opportunity.objects.filter(bintang_sale_id="POS-ORD-ABC123").count(), 1)

    def test_langsung_lunas_membuat_opportunity_won(self):
        self._kirim(True, sale_id="POS-ORD-LUNAS")
        self.assertEqual(Opportunity.objects.get(bintang_sale_id="POS-ORD-LUNAS").stage_id, self.stage_won.id)

    def test_penjual_punya_akun_crm_jadi_pemilik_selain_itu_akun_atasan(self):
        self._kirim(False, penjual=44)
        opp = Opportunity.objects.get(bintang_sale_id="POS-ORD-ABC123")
        self.assertEqual(opp.owner_id, self.staff.id)
        self.assertEqual(Contact.objects.get(bintang_contact_id="6281300000001").contact_owner_id, self.staff.id)

        # Penjual tanpa akun CRM (kasir) -> pemilik bawaan = akun atasan.
        self._post({"nomor_wa": "6281300000002", "nama": "Kasir Order",
                    "penjual_hr_employee_id": 21,
                    "sale": {"id": "POS-ORD-KASIR", "nomor": "POS-ORD-KASIR", "total": 50000, "lunas": False}})
        self.assertEqual(Opportunity.objects.get(bintang_sale_id="POS-ORD-KASIR").owner_id, self.owner.id)

    def test_id_order_40_karakter_muat(self):
        sale_id = "POS-ORD-" + "A" * 32
        self.assertEqual(len(sale_id), 40)
        self.assertEqual(self._kirim(False, sale_id=sale_id).status_code, status.HTTP_201_CREATED)


class BintangBridgePelangganBaruTests(BintangBridgeSaleTests):
    """Pelanggan baru ERP (tanpa penjualan) masuk CRM sebagai Contact saja (2026-11-02)."""

    def test_pelanggan_baru_membuat_contact_tanpa_opportunity(self):
        r = self._post({
            "nomor_wa": "6281234500001", "nama": "Rina Wulandari", "email": "rina@contoh.com",
            "kota": "Bandung", "kode_pelanggan": "PLG-77", "nama_perusahaan": "CV Maju", "sumber": "erp-pelanggan",
        })
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertIsNone(r.data["opportunity_id"])
        contact = Contact.objects.get(bintang_contact_id="6281234500001")
        self.assertEqual(contact.first_name, "Rina")
        self.assertEqual(contact.email, "rina@contoh.com")
        self.assertEqual(contact.address_city, "Bandung")
        self.assertEqual(contact.contact_source, "other")
        self.assertIn("kode PLG-77", contact.description)
        self.assertIn("CV Maju", contact.description)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_nomor_format_beda_tetap_satu_contact(self):
        self._post({"nomor_wa": "081234500002", "nama": "Doni Pratama"})
        for varian in ("6281234500002", "+62 812-3450-0002", "81234500002"):
            r = self._post({"nomor_wa": varian, "nama": "Doni Pratama"})
            self.assertEqual(r.status_code, status.HTTP_200_OK, (varian, r.data))
            self.assertFalse(r.data["contact_created"], varian)
        self.assertEqual(Contact.objects.count(), 1)
        # Kunci ERP pertama tidak diganti: kiriman berikutnya tetap cocok lewat normalisasi.
        self.assertEqual(Contact.objects.get().bintang_contact_id, "081234500002")

    def test_nomor_berbeda_tetap_contact_berbeda(self):
        self._post({"nomor_wa": "081234500003", "nama": "A"})
        self._post({"nomor_wa": "081234500004", "nama": "B"})
        self.assertEqual(Contact.objects.count(), 2)


class BintangBridgePeluangJelasTests(BintangBridgeSaleTests):
    """Peluang dari order ERP memuat pelanggan, rincian item, pembayaran, dan langkah berikutnya."""

    def setUp(self):
        super().setUp()
        self.stage_open = OpportunityStage.objects.create(
            name="Negotiation", order=1, probability=50, stage_type="open",
        )

    def _kirim(self, lunas, dp=50000, sisa=150000, status_order="Dalam Proses Produksi"):
        return self._post({
            "nomor_wa": "6281300000009", "nama": "Dinda Foto", "email": "dinda@contoh.com",
            "sale": {
                "id": "POS-ORD-JELAS", "nomor": "POS-ORD-JELAS", "total": 200000, "tanggal": "2026-11-02",
                "lunas": lunas, "unit_bisnis": "StarFoto", "pelanggan": "Dinda Foto",
                "status_order": status_order, "dp_dibayar": dp, "sisa_tagihan": sisa,
                "metode_pembayaran": "tunai", "dilayani_oleh": "Kasir Foto", "catatan": "Cetak 2 rangkap",
                "items": [
                    {"nama": "Cetak Foto 4R", "qty": 10, "subtotal": 50000},
                    {"nama": "Pigura 10R", "qty": 1.5, "subtotal": 150000},
                ],
            },
        })

    def test_peluang_baru_berisi_rincian(self):
        r = self._kirim(False)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        opp = Opportunity.objects.get(bintang_sale_id="POS-ORD-JELAS")
        self.assertEqual(opp.name, "Dinda Foto - StarFoto POS-ORD-JELAS")
        self.assertEqual(opp.lead_source, "kasir")
        self.assertEqual(opp.email, "dinda@contoh.com")
        self.assertEqual(float(opp.quantity), 11.5)
        self.assertEqual(opp.next_step, "Menunggu pelunasan sisa Rp. 150.000 (Dalam Proses Produksi)")
        for potongan in (
            "Pelanggan: Dinda Foto - WA 6281300000009", "Dilayani oleh: Kasir Foto",
            "- Cetak Foto 4R x 10 = Rp. 50.000", "- Pigura 10R x 1.5 = Rp. 150.000",
            "Total tagihan: Rp. 200.000", "Sudah dibayar: Rp. 50.000", "Sisa tagihan: Rp. 150.000",
            "Catatan pelanggan: Cetak 2 rangkap",
        ):
            self.assertIn(potongan, opp.description)

    def test_lunas_memperbarui_rincian_lalu_closed_won(self):
        self._kirim(False)
        self._kirim(True, dp=200000, sisa=0, status_order="Selesai Seluruhnya")
        opp = Opportunity.objects.get(bintang_sale_id="POS-ORD-JELAS")
        self.assertEqual(opp.stage_id, self.stage_won.id)
        self.assertEqual(opp.next_step, "Lunas - tidak ada tagihan tersisa")
        self.assertIn("Sudah dibayar: Rp. 200.000", opp.description)
        self.assertIn("Sisa tagihan: Rp. 0", opp.description)
        self.assertEqual(Opportunity.objects.count(), 1)

    def test_kiriman_lama_tanpa_rincian_tidak_menimpa_deskripsi(self):
        self._kirim(False)
        self._post({
            "nomor_wa": "6281300000009", "nama": "Dinda Foto",
            "sale": {"id": "POS-ORD-JELAS", "nomor": "POS-ORD-JELAS", "total": 250000, "lunas": False, "unit_bisnis": "StarFoto"},
        })
        opp = Opportunity.objects.get(bintang_sale_id="POS-ORD-JELAS")
        self.assertEqual(float(opp.amount), 250000.0)
        self.assertIn("Rincian pesanan:", opp.description)
        self.assertEqual(opp.name, "Dinda Foto - StarFoto POS-ORD-JELAS")


class BintangRingkasanTests(TestCase):
    def test_rupiah_dan_normalisasi(self):
        from horilla.contrib.core.views.bintang_bridge import normalisasi_nomor
        from horilla_crm.opportunities.bintang_ringkasan import rupiah

        self.assertEqual(rupiah(1250000), "Rp. 1.250.000")
        self.assertEqual(rupiah(None), "Rp. 0")
        self.assertEqual(normalisasi_nomor("0812-3456-7890"), "6281234567890")
        self.assertEqual(normalisasi_nomor("+62 812 3456 7890"), "6281234567890")
        self.assertEqual(normalisasi_nomor("81234567890"), "6281234567890")
