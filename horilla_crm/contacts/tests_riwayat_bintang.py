"""Tab Riwayat Bintang di detail Contact (2026-09-26, UAT SLS-04). Klien Bintang di-mock."""

from unittest import mock

from django.contrib.auth.models import Permission
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.user import HorillaUser
from horilla_crm.contacts.models import Contact
from horilla_crm.opportunities import bintang_order

H = {"HTTP_HX_REQUEST": "true", "secure": True}
DATA = {
    "nomor": "6281234567890", "pelanggan": "Budi", "terdaftar": True, "jumlah_transaksi": 2,
    "total_belanja_lunas": 155000, "sisa_tagihan": 20000, "pertama": "2026-08-01T10:00:00", "terakhir": "2026-09-20T10:00:00",
    "riwayat": [
        {"jenis": "order", "id": "ORD-1", "waktu": "2026-09-20T10:00:00", "kanal": "CRM / Sales", "status": "Proses",
         "total": 125000, "sisa": 20000, "lunas": False, "batal": False, "ringkasan": "Banner x2"},
        {"jenis": "pos", "id": "POS-9", "waktu": "2026-08-01T10:00:00", "kanal": "Kasir (POS)", "status": "Lunas",
         "total": 30000, "sisa": 0, "lunas": True, "batal": False, "ringkasan": "Stiker x10"},
    ],
}


class RiwayatBintangTabTests(TestCase):
    def setUp(self):
        from login_history.models import post_login

        user_logged_in.disconnect(post_login)
        self.addCleanup(user_logged_in.connect, post_login)
        self.company = Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com")
        self.sales = self._user("tim.sales")
        self.lain = self._user("sales.lain")
        self.contact = Contact.objects.create(
            first_name="Budi", last_name="Santoso", email="budi@contoh.id", contact_number="0812-3456-7890",
            contact_owner=self.sales, company=self.company,
        )

    def _user(self, username):
        u = HorillaUser.objects.create(username=username, first_name="Tim", last_name="Sales", company=self.company)
        u.user_permissions.add(*Permission.objects.filter(codename="view_own_contact", content_type__app_label="contacts"))
        return HorillaUser.objects.get(pk=u.pk)

    def _get(self, user):
        self.client.force_login(user)
        s = self.client.session
        s["active_company_id"] = self.company.pk
        s.save()
        return self.client.get(reverse("contacts:riwayat_bintang_tab", args=[self.contact.pk]), **H)

    @mock.patch.object(bintang_order, "riwayat_pelanggan", return_value=DATA)
    def test_pemilik_melihat_riwayat(self, m):
        res = self._get(self.sales)
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        for teks in ("ORD-1", "POS-9", "Kasir (POS)", "Banner x2", "Rp 155.000", "Rp 20.000"):
            self.assertIn(teks, html)
        m.assert_called_once_with("0812-3456-7890")

    @mock.patch.object(bintang_order, "riwayat_pelanggan")
    def test_sales_lain_ditolak(self, m):
        self.assertEqual(self._get(self.lain).status_code, 403)
        m.assert_not_called()

    @mock.patch.object(bintang_order, "riwayat_pelanggan", side_effect=bintang_order.BintangOrderError("Bintang tidak bisa dihubungi."))
    def test_bintang_mati(self, _m):
        self.assertIn("Bintang tidak bisa dihubungi.", self._get(self.sales).content.decode())

    @mock.patch.object(bintang_order, "riwayat_pelanggan")
    def test_tanpa_nomor(self, m):
        Contact.all_objects.filter(pk=self.contact.pk).update(contact_number="")
        self.assertIn("belum punya nomor HP", self._get(self.sales).content.decode())
        m.assert_not_called()

    def test_tab_muncul_di_detail_contact(self):
        self.client.force_login(self.sales)
        res = self.client.get(reverse("contacts:contact_detail_view_tabs"), {"object_id": self.contact.pk},
                              HTTP_HX_REQUEST="true", secure=True, follow=True)
        self.assertIn(reverse("contacts:riwayat_bintang_tab", args=[self.contact.pk]), res.content.decode())
