"""Tab Order Bintang di Opportunity (2026-09-26): Sales membuat & memantau order
yang dikirim ke Bintang. Klien Bintang di-mock."""

import datetime
from unittest import mock

from django.contrib.auth.models import Permission
from django.contrib.auth.signals import user_logged_in
from django.test import TestCase
from django.urls import reverse

from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.user import HorillaUser
from horilla_crm.opportunities import bintang_order
from horilla_crm.opportunities.models import Opportunity, OpportunityStage

H = {"HTTP_HX_REQUEST": "true", "secure": True}


class OrderBintangTabTests(TestCase):
    def setUp(self):
        # login_history mencatat User-Agent saat login; force_login tidak punya header itu.
        from login_history.models import post_login

        user_logged_in.disconnect(post_login)
        self.addCleanup(user_logged_in.connect, post_login)
        self.company = Company.objects.create(name="Star Photo & Advertising", email="info@contoh.com")
        stage = OpportunityStage.objects.create(name="Prospecting", order=1, probability=10, stage_type="open")
        self.sales = self._user("tim.sales", ["view_own_opportunity", "change_own_opportunity"])
        self.lain = self._user("sales.lain", ["view_own_opportunity", "change_own_opportunity"])
        self.opp = Opportunity.objects.create(
            name="Banner Toko Budi", amount=0, close_date=datetime.date(2026, 10, 1), stage=stage,
            probability=10, owner=self.sales, company=self.company,
        )

    def _user(self, username, perms):
        u = HorillaUser.objects.create(username=username, first_name="Tim", last_name="Sales", company=self.company)
        u.user_permissions.add(*Permission.objects.filter(codename__in=perms, content_type__app_label="opportunities"))
        return HorillaUser.objects.get(pk=u.pk)

    def _as(self, user):
        self.client.force_login(user)
        s = self.client.session
        s["active_company_id"] = self.company.pk
        s.save()

    @mock.patch.object(bintang_order, "order_per_opportunity")
    def test_tab_menampilkan_order_prospek(self, m):
        m.return_value = [{"id": "ORD-1", "status_label": "Draft Penawaran", "total_harga": 125000,
                           "sisa_tagihan": 125000, "lunas": False, "waktu": "2026-09-26T10:00:00",
                           "items": [{"nama": "Banner", "qty": 2}], "sales_nama": "Tim Sales"}]
        self._as(self.sales)
        res = self.client.get(reverse("opportunities:order_bintang_tab", args=[self.opp.pk]), **H)
        self.assertEqual(res.status_code, 200)
        html = res.content.decode()
        self.assertIn("ORD-1", html)
        self.assertIn("Rp 125.000", html)
        self.assertIn(reverse("opportunities:order_bintang_form", args=[self.opp.pk]), html)
        m.assert_called_once_with(self.opp.pk)

    @mock.patch.object(bintang_order, "order_per_opportunity", side_effect=bintang_order.BintangOrderError("Bintang tidak bisa dihubungi."))
    def test_tab_saat_bintang_mati_tampil_pesan(self, _m):
        self._as(self.sales)
        res = self.client.get(reverse("opportunities:order_bintang_tab", args=[self.opp.pk]), **H)
        self.assertIn("Bintang tidak bisa dihubungi.", res.content.decode())

    @mock.patch.object(bintang_order, "buat_order")
    def test_kirim_order_membawa_identitas_sales_tanpa_harga(self, m):
        m.return_value = {"id": "ORD-2"}
        self._as(self.sales)
        res = self.client.post(reverse("opportunities:order_bintang_form", args=[self.opp.pk]), {
            "kunci": "crm-opp-x", "nama": "Budi", "nomor_hp": "0812", "email": "", "catatan": "Jumat",
            "product_id": ["5", "6"], "product_nama": ["Banner", "Stiker"], "qty": ["2", "10"],
            "keterangan": ["3x1 m", ""], "harga": ["1", "1"],
        }, **H)
        self.assertEqual(res.status_code, 200)
        self.assertIn("closeModal", res.content.decode())
        payload = m.call_args.args[0]
        self.assertEqual(payload["crm_opportunity_id"], self.opp.pk)
        self.assertEqual(payload["crm_user_id"], self.sales.pk)
        self.assertEqual(payload["kunci"], "crm-opp-x")
        self.assertEqual(payload["items"], [
            {"product_id": "5", "qty": "2", "keterangan": "3x1 m"},
            {"product_id": "6", "qty": "10", "keterangan": ""},
        ])
        self.assertNotIn("harga", str(payload["items"]))

    @mock.patch.object(bintang_order, "buat_order", side_effect=bintang_order.BintangOrderError("Nomor HP/WA pelanggan tidak valid."))
    def test_penolakan_bintang_ditampilkan_di_form(self, _m):
        self._as(self.sales)
        res = self.client.post(reverse("opportunities:order_bintang_form", args=[self.opp.pk]), {
            "kunci": "k", "nama": "Budi", "nomor_hp": "1", "product_id": ["5"], "product_nama": ["Banner"],
            "qty": ["1"], "keterangan": [""],
        }, **H)
        self.assertIn("Nomor HP/WA pelanggan tidak valid.", res.content.decode())

    @mock.patch.object(bintang_order, "buat_order")
    @mock.patch.object(bintang_order, "order_per_opportunity", return_value=[])
    def test_sales_lain_tidak_bisa_melihat_atau_membuat_order(self, _lihat, buat):
        self._as(self.lain)
        self.assertEqual(self.client.get(reverse("opportunities:order_bintang_tab", args=[self.opp.pk]), **H).status_code, 403)
        res = self.client.post(reverse("opportunities:order_bintang_form", args=[self.opp.pk]), {"kunci": "k"}, **H)
        self.assertEqual(res.status_code, 403)
        buat.assert_not_called()

    @mock.patch.object(bintang_order, "cari_produk", return_value=[{"id": 5, "nama": "Banner"}])
    def test_cari_produk(self, m):
        self._as(self.sales)
        # Middleware CRM menambah ?section=... lewat 302; fetch() di browser mengikutinya.
        res = self.client.get(reverse("opportunities:produk_bintang_cari"), {"q": "ban"}, secure=True, follow=True)
        self.assertEqual(res.json()["hasil"][0]["nama"], "Banner")
        self.assertEqual(self.client.get(reverse("opportunities:produk_bintang_cari"), {"q": "b"}, secure=True, follow=True).json()["hasil"], [])
