"""Setelah sandi diganti lewat tautan email, tampilkan halaman "login ulang" (2026-10-13)."""

from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.user import HorillaUser


class SandiDiperbaruiTests(TestCase):
    def setUp(self):
        company = Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com")
        self.user = HorillaUser.objects.create(username="reset.uji", email="reset@uji.test", company=company)
        self.user.set_password("SandiLama#2026a")
        self.user.save()
        self.url = reverse(
            "core:password_reset_confirm",
            args=[urlsafe_base64_encode(force_bytes(self.user.pk)), default_token_generator.make_token(self.user)],
        )
        self.baru = {"new_password": "SandiBaru#2026xyz", "confirm_password": "SandiBaru#2026xyz"}

    def test_selesai_reset_mengarah_ke_halaman_login_ulang_bukan_satu_aplikasi(self):
        res = self.client.post(self.url, self.baru, secure=True)
        self.assertRedirects(res, reverse("core:password_updated"), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("SandiBaru#2026xyz"))

    def test_lewat_htmx_memakai_hx_redirect(self):
        res = self.client.post(self.url, self.baru, secure=True, HTTP_HX_REQUEST="true")
        self.assertEqual(res["HX-Redirect"], reverse("core:password_updated"))

    def test_halaman_publik_menyebut_semua_aplikasi(self):
        html = self.client.get(reverse("core:password_updated"), secure=True).content.decode()
        self.assertIn("Sandi Anda telah diperbarui", html)
        self.assertIn("login ulang di aplikasi ERP, HR, CRM, atau aplikasi mobile", html)
        self.assertIn('href="https://app.starphotoadvertising.com"', html)
        self.assertIn('href="https://hr.starphotoadvertising.com"', html)

    def test_sandi_lemah_tetap_di_form(self):
        res = self.client.post(self.url, {"new_password": "123", "confirm_password": "123"}, secure=True)
        self.assertEqual(res.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("SandiLama#2026a"))
