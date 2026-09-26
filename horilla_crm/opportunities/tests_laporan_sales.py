"""Laporan Sales & Marketing (2026-09-26, UAT SLS-01/02). Klien Bintang di-mock."""

import datetime
from unittest import mock

from django.urls import reverse

from horilla_crm.opportunities import bintang_order
from horilla_crm.opportunities.models import Opportunity, OpportunityStage
from horilla_crm.opportunities.tests_order_bintang import _DasarOrderBintang

LAPORAN = {
    "mulai": "2026-09-01", "selesai": "2026-09-30",
    "ringkasan": {"transaksi": 3, "omzet": 215000, "dibayar": 90000, "belum_dibayar": 125000,
                  "pelanggan_aktif": 2, "pelanggan_baru": 1, "pelanggan_kembali": 1,
                  "pelanggan_terdaftar_baru": 4, "pelanggan_terdaftar_total": 120},
    "per_kanal": [{"kanal": "CRM / Sales", "transaksi": 1, "omzet": 125000, "dibayar": 0},
                  {"kanal": "Kasir (POS)", "transaksi": 1, "omzet": 30000, "dibayar": 30000}],
    "per_bulan": [{"bulan": "2026-09", "transaksi": 3, "omzet": 215000, "pelanggan_baru": 1}],
}


class LaporanSalesTests(_DasarOrderBintang):
    def _get(self, **params):
        return self.client.get(reverse("opportunities:laporan_sales"), params, secure=True, follow=True)

    @mock.patch.object(bintang_order, "rekap_sales")
    @mock.patch.object(bintang_order, "laporan_penjualan", return_value=LAPORAN)
    def test_spv_melihat_laporan_lengkap(self, laporan, rekap):
        rekap.return_value = {self.sales.pk: {"crm_user_id": self.sales.pk, "jumlah_order": 2, "jumlah_lunas": 1,
                                              "nilai_lunas": 50000, "nilai_belum_lunas": 75000}}
        won = OpportunityStage.objects.create(name="Closed Won", order=9, probability=100, stage_type="won", company=self.company)
        Opportunity.all_objects.filter(pk=self.opp.pk).update(stage=won, amount=125000, close_date=datetime.date(2026, 9, 20))
        spv = self._user("spv.uji", ["view_opportunity"])
        self._as(spv)
        html = self._get(mulai="2026-09-01", selesai="2026-09-30").content.decode()
        for teks in ("Rp 215.000", "Rp 125.000", "CRM / Sales", "Kasir (POS)", "58.1%", "2026-09",
                     "Tim Sales", "Rp 50.000", "Rp 75.000", "(+4 periode ini)"):
            self.assertIn(teks, html)
        laporan.assert_called_once_with(datetime.date(2026, 9, 1), datetime.date(2026, 9, 30))
        self.assertEqual(rekap.call_args.args[2], [])

    @mock.patch.object(bintang_order, "laporan_penjualan", side_effect=bintang_order.BintangOrderError("Bintang tidak bisa dihubungi."))
    def test_bintang_mati_bagian_crm_tetap_tampil(self, _m):
        spv = self._user("spv.uji", ["view_opportunity"])
        self._as(spv)
        html = self._get().content.decode()
        self.assertIn("Bintang tidak bisa dihubungi.", html)
        self.assertIn("Lead baru", html)

    @mock.patch.object(bintang_order, "laporan_penjualan")
    def test_sales_biasa_tidak_bisa_membuka(self, m):
        self._as(self.sales)
        self._get()
        m.assert_not_called()

    @mock.patch.object(bintang_order, "laporan_penjualan")
    def test_periode_terbalik_ditolak(self, m):
        spv = self._user("spv.uji", ["view_opportunity"])
        self._as(spv)
        self.assertIn("Tanggal mulai harus sebelum tanggal selesai.", self._get(mulai="2026-10-01", selesai="2026-09-01").content.decode())
        m.assert_not_called()
