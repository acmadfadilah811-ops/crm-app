"""Pusat Bantuan CRM: isi sesuai peran, semua tautan halaman valid (2026-10-05)."""
from django.contrib.auth.models import Permission
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from horilla.contrib.core import bantuan
from horilla.contrib.core.models.user import HorillaUser


class PusatBantuanCrmTests(TestCase):
    def setUp(self):
        # login_history mencatat User-Agent saat login; force_login tidak punya header itu.
        from login_history.models import post_login

        user_logged_in.disconnect(post_login)
        self.addCleanup(user_logged_in.connect, post_login)
        self.user = HorillaUser.objects.create(username="crm.bantuan")
        self.user.set_password("SandiUji12345")
        self.user.save()

    def test_semua_nama_halaman_katalog_bisa_di_reverse(self):
        for entri in bantuan.KATALOG:
            if entri.get("halaman"):
                reverse(entri["halaman"])  # NoReverseMatch = katalog basi
            self.assertTrue(entri.get("halaman") or entri.get("url_luar"), entri["id"])
            self.assertIn(entri["modul"], bantuan.URUTAN_MODUL, entri["id"])

    def test_sales_tidak_melihat_layanan_pengelola(self):
        self.assertEqual(bantuan.peran_pengguna(self.user), ["sales"])
        ids = {l["id"] for l in bantuan.katalog_untuk(self.user)}
        self.assertIn("buat-order", ids)
        self.assertNotIn("laporan-sales", ids)

    def test_pengelola_melihat_semua(self):
        perm = Permission.objects.get(codename="view_opportunity", content_type__app_label="opportunities")
        self.user.user_permissions.add(perm)
        self.user = HorillaUser.objects.get(pk=self.user.pk)
        self.assertEqual(bantuan.peran_pengguna(self.user), ["sales", "pengelola"])
        self.assertEqual(len(bantuan.katalog_untuk(self.user)), len(bantuan.KATALOG))

    def test_widget_tampil_setelah_login_dan_tidak_di_halaman_login(self):
        res = self.client.get(reverse("core:login"), secure=True)
        self.assertNotIn('id="pb-tombol"', res.content.decode())
        self.client.force_login(self.user)
        res = self.client.get("/", secure=True, follow=True)
        html = res.content.decode()
        self.assertIn('id="pb-tombol"', html)
        self.assertIn("Buat order ke ERP dari peluang", html)
        self.assertNotIn("Laporan sales", html)
