"""Tautan "Lupa password" di login CRM & email reset (2026-09-28).

Sebelumnya tautan hanya muncul bila konfigurasi email tertaut ke perusahaan
pusat; konfigurasi utama tanpa perusahaan (kondisi produksi) membuatnya
tersembunyi. Email reset juga masih berjudul "Horilla"."""

from django.core import mail
from django.test import Client, TestCase, override_settings

from horilla.contrib.core.models import Company
from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.mail.models import HorillaMailConfiguration

UA = {"HTTP_USER_AGENT": "pytest"}


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LupaPasswordTests(TestCase):
    def setUp(self):
        self.client = Client(**UA)
        Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com", hq=True)

    def _konfigurasi_utama_tanpa_perusahaan(self):
        HorillaMailConfiguration.objects.create(
            host="smtp.contoh.com", port=587, from_email="crm@contoh.com", is_primary=True,
        )

    def test_tautan_tersembunyi_tanpa_konfigurasi_email(self):
        res = self.client.get("/login/", secure=True)
        self.assertNotContains(res, "forgot-password")

    def test_tautan_muncul_dengan_konfigurasi_utama_tanpa_perusahaan(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        res = self.client.get("/login/", secure=True)
        self.assertContains(res, "forgot-password")

    def test_email_reset_berjudul_crm_bukan_horilla(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        HorillaUser.objects.create(username="sales.uji", email="sales.uji@contoh.com")
        self.client.post("/forgot-password/", {"email": "sales.uji"}, secure=True)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("CRM Star Photo & Advertising", mail.outbox[0].subject)
        self.assertNotIn("Horilla", mail.outbox[0].subject)
        pesan = mail.outbox[0]
        # Teks biasa berisi tautan + versi HTML (multipart), Message-ID ber-domain.
        self.assertIn("/reset-password/", pesan.body)
        self.assertEqual([t for _, t in pesan.alternatives], ["text/html"])
        self.assertNotIn("<html", pesan.body.lower())
        self.assertTrue(pesan.extra_headers["Message-ID"].endswith("@testserver>"))
