"""Target Sales (2026-09-26, UAT SLS-05/06). Klien Bintang di-mock."""

import datetime
from unittest import mock

from django.urls import reverse

from horilla.contrib.core.models.organization import Role
from horilla_crm.opportunities import bintang_order
from horilla_crm.opportunities.target_models import TargetSales
from horilla_crm.opportunities.tests_order_bintang import H, _DasarOrderBintang

HARI_INI = datetime.date.today()


class TargetSalesTests(_DasarOrderBintang):
    def setUp(self):
        super().setUp()
        role = Role.objects.create(role_name="Tim Sales Uji", company=self.company)
        for u in (self.sales, self.lain):
            u.role = role
            u.save()
        self.spv = self._user("spv.uji", ["view_opportunity", "change_opportunity"])
        self.target = TargetSales.objects.create(
            sales=self.sales, nama_periode="Periode uji", tanggal_mulai=HARI_INI - datetime.timedelta(days=5),
            tanggal_selesai=HARI_INI + datetime.timedelta(days=10), target_nilai=1000000, target_jumlah_order=4,
        )
        TargetSales.objects.create(
            sales=self.lain, nama_periode="Periode lain", tanggal_mulai=HARI_INI,
            tanggal_selesai=HARI_INI, target_nilai=0, target_jumlah_order=2,
        )

    def _halaman(self, **params):
        return self.client.get(reverse("opportunities:target_sales"), params, secure=True, follow=True)

    def _simpan(self, pk=None, **data):
        isi = {"sales": self.lain.pk, "nama_periode": "Oktober", "tanggal_mulai": "2026-10-01",
               "tanggal_selesai": "2026-10-31", "target_nilai": "5000000", "target_jumlah_order": "10", "catatan": ""}
        isi.update(data)
        url = reverse("opportunities:target_sales_ubah", args=[pk]) if pk else reverse("opportunities:target_sales_tambah")
        return self.client.post(url, isi, **H)

    @mock.patch.object(bintang_order, "rekap_sales")
    def test_sales_melihat_target_sendiri_dengan_realisasi(self, rekap):
        rekap.return_value = {self.sales.pk: {"crm_user_id": self.sales.pk, "jumlah_order": 3, "jumlah_lunas": 2,
                                              "nilai_lunas": 250000, "nilai_belum_lunas": 80000}}
        self._as(self.sales)
        html = self._halaman().content.decode()
        self.assertIn("Periode uji", html)
        self.assertNotIn("Periode lain", html)
        self.assertIn("Rp 250.000 / Rp 1.000.000", html)
        self.assertIn("(25.0%)", html)
        self.assertIn("3 / 4 order", html)
        self.assertIn("Rp 80.000", html)
        self.assertNotIn("Tambah Target", html)
        args = rekap.call_args.args
        self.assertEqual((args[0], args[1], args[2]), (self.target.tanggal_mulai, self.target.tanggal_selesai, [self.sales.pk]))

    @mock.patch.object(bintang_order, "rekap_sales", return_value={})
    def test_spv_melihat_semua_dan_bisa_filter(self, _rekap):
        self._as(self.spv)
        html = self._halaman().content.decode()
        self.assertIn("Periode uji", html)
        self.assertIn("Periode lain", html)
        self.assertIn("Tambah Target", html)
        html = self._halaman(sales=self.lain.pk).content.decode()
        self.assertNotIn("Periode uji", html)

    @mock.patch.object(bintang_order, "rekap_sales", side_effect=bintang_order.BintangOrderError("Bintang tidak bisa dihubungi."))
    def test_bintang_mati_tetap_tampil_dengan_pesan(self, _rekap):
        self._as(self.sales)
        html = self._halaman().content.decode()
        self.assertIn("Periode uji", html)
        self.assertIn("Bintang tidak bisa dihubungi.", html)

    def test_spv_tambah_ubah_hapus_target(self):
        self._as(self.spv)
        res = self._simpan()
        self.assertIn("closeModal", res.content.decode())
        baru = TargetSales.objects.get(nama_periode="Oktober")
        self.assertEqual((baru.sales_id, int(baru.target_nilai), baru.target_jumlah_order, baru.dibuat_oleh_id),
                         (self.lain.pk, 5000000, 10, self.spv.pk))
        self._simpan(pk=baru.pk, target_jumlah_order="12")
        baru.refresh_from_db()
        self.assertEqual(baru.target_jumlah_order, 12)
        self.client.post(reverse("opportunities:target_sales_hapus", args=[baru.pk]), **H)
        self.assertFalse(TargetSales.objects.filter(pk=baru.pk).exists())

    def test_validasi_periode_dan_target(self):
        self._as(self.spv)
        html = self._simpan(tanggal_mulai="2026-11-01").content.decode()
        self.assertIn("Tanggal mulai harus sebelum tanggal selesai.", html)
        html = self._simpan(target_nilai="0", target_jumlah_order="0").content.decode()
        self.assertIn("Isi target nilai, target jumlah order, atau keduanya.", html)
        self.assertFalse(TargetSales.objects.filter(nama_periode="Oktober").exists())

    def test_sales_tidak_bisa_mengatur_target(self):
        self._as(self.sales)
        self._simpan(sales=self.sales.pk, target_nilai="999999999")
        self.client.post(reverse("opportunities:target_sales_hapus", args=[self.target.pk]), **H)
        self.assertFalse(TargetSales.objects.filter(nama_periode="Oktober").exists())
        self.assertTrue(TargetSales.objects.filter(pk=self.target.pk).exists())
