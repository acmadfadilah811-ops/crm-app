"""Tautan "Lupa password" di login CRM & email reset (2026-09-28).

- Tautan tampil juga bila konfigurasi email utama belum tertaut perusahaan.
- Akun tidak terdaftar / belum punya email diberi tahu (permintaan user).
- Email reset teks biasa pendek (versi HTML masuk spam & terlambat).
- Dibatasi 1 permintaan per menit."""

from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings

from horilla.contrib.core.models import Company
from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.mail.models import HorillaMailConfiguration

UA = {"HTTP_USER_AGENT": "pytest"}


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class LupaPasswordTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.client = Client(**UA)
        Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com", hq=True)

    def _konfigurasi_utama_tanpa_perusahaan(self):
        HorillaMailConfiguration.objects.create(
            host="smtp.contoh.com", port=587, from_email="crm@contoh.com", is_primary=True,
        )

    def _minta(self, isian, ip="10.0.0.1"):
        return self.client.post("/forgot-password/", {"email": isian}, secure=True, HTTP_X_FORWARDED_FOR=ip)

    def test_tautan_tersembunyi_tanpa_konfigurasi_email(self):
        res = self.client.get("/login/", secure=True)
        self.assertNotContains(res, "forgot-password")

    def test_tautan_muncul_dengan_konfigurasi_utama_tanpa_perusahaan(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        res = self.client.get("/login/", secure=True)
        self.assertContains(res, "forgot-password")

    def test_email_reset_teks_biasa_bermerek_crm(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        HorillaUser.objects.create(username="sales.uji", email="sales.uji@contoh.com")
        res = self._minta("Sales.Uji")  # username tidak peka huruf besar
        self.assertContains(res, "s***i@contoh.com")
        self.assertEqual(len(mail.outbox), 1)
        pesan = mail.outbox[0]
        self.assertEqual(pesan.subject, "Reset Password - CRM Star Photo & Advertising")
        self.assertIn("/reset-password/", pesan.body)
        self.assertIn("sales.uji", pesan.body)
        self.assertEqual(getattr(pesan, "alternatives", []), [])
        self.assertTrue(pesan.extra_headers["Message-ID"].endswith("@testserver>"))

    def test_akun_tidak_terdaftar_diberi_tahu(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        res = self._minta("tidak.ada@contoh.com")
        self.assertContains(res, "tidak terdaftar")
        self.assertEqual(len(mail.outbox), 0)

    def test_akun_tanpa_email_diberi_tahu(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        HorillaUser.objects.create(username="tanpa.email", email="")
        res = self._minta("tanpa.email")
        self.assertContains(res, "belum punya email")
        self.assertEqual(len(mail.outbox), 0)

    def test_dibatasi_sekali_per_menit(self):
        self._konfigurasi_utama_tanpa_perusahaan()
        HorillaUser.objects.create(username="sales.uji", email="sales.uji@contoh.com")
        self._minta("sales.uji", ip="10.0.0.1")
        res = self._minta("sales.uji", ip="10.0.0.2")  # IP lain, akun sama
        self.assertContains(res, "Tunggu 1 menit")
        res = self._minta("lain@contoh.com", ip="10.0.0.1")  # IP sama, akun lain
        self.assertContains(res, "Tunggu 1 menit")
        self.assertEqual(len(mail.outbox), 1)
