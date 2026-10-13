"""Follow up pelanggan yang lama tidak order + KPI omzet di dasbor (2026-10-13). Klien Bintang di-mock."""

import datetime
from unittest import mock

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.dashboard.utils import DefaultDashboardGenerator
from horilla.contrib.notifications.models import Notification
from horilla_crm.contacts.models import Contact
from horilla_crm.opportunities import bintang_order
from horilla_crm.opportunities import followup as svc
from horilla_crm.opportunities.followup_models import PelangganFollowUp as F
from horilla_crm.opportunities.followup_models import PengaturanFollowUp
from horilla_crm.opportunities.tests_order_bintang import H, _DasarOrderBintang

HARI_INI = datetime.date.today()
MEMORI = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


def _item(nomor, nama, hari, jumlah=2, total=500000):
    return {
        "nomor": nomor, "nama": nama, "terakhir": (HARI_INI - datetime.timedelta(days=hari)).isoformat(),
        "hari_sejak": hari, "jumlah_transaksi": jumlah, "total_belanja": total,
    }


def _jawab(*items, dipotong=False):
    return {"hari": 60, "min_transaksi": 1, "total": len(items), "dipotong": dipotong, "hasil": list(items)}


@override_settings(CHANNEL_LAYERS=MEMORI)
class _DasarFollowUp(_DasarOrderBintang):
    def setUp(self):
        super().setUp()
        cache.clear()
        for u in (self.sales, self.lain):
            u.user_permissions.add(*self._izin(["view_own_contact"], "contacts"))
        self.spv = self._user("spv.uji", ["view_opportunity", "change_opportunity"])
        self.spv.user_permissions.add(*self._izin(["view_contact", "view_own_contact"], "contacts"))
        self.spv = HorillaUser.objects.get(pk=self.spv.pk)
        self.contact = Contact.objects.create(
            first_name="Budi", last_name="Santoso", contact_owner=self.sales, company=self.company,
            contact_number="081234567890", bintang_contact_id="081234567890", email="budi@x.test",
        )

    def _izin(self, kode, app):
        from django.contrib.auth.models import Permission

        return Permission.objects.filter(codename__in=kode, content_type__app_label=app)

    def _sinkron(self, *items, **kw):
        with mock.patch.object(bintang_order, "pelanggan_dorman", return_value=_jawab(*items, **kw)) as m:
            ringkas = svc.sinkron_dorman()
        return ringkas, m


class SinkronTests(_DasarFollowUp):
    def test_pelanggan_dorman_dibuat_dan_dicocokkan_ke_contact_pemilik(self):
        ringkas, m = self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70, total=100000))
        self.assertEqual(ringkas["baru"], 2)
        m.assert_called_once_with(60, 1)
        budi = F.objects.get(nomor="6281234567890")
        self.assertEqual((budi.contact_id, budi.pemilik_id, budi.status), (self.contact.pk, self.sales.pk, F.BARU))
        self.assertEqual((budi.hari_sejak, budi.jumlah_transaksi, int(budi.total_belanja)), (90, 2, 500000))
        sari = F.objects.get(nomor="6285700001111")
        self.assertEqual((sari.contact_id, sari.pemilik_id), (None, None))

    def test_notifikasi_ke_pemilik_dan_atasan_sekali_saja(self):
        self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70))
        ke_sales = Notification.objects.filter(user=self.sales)
        self.assertEqual(ke_sales.count(), 1)
        self.assertIn("1 pelanggan lama tidak order", ke_sales.get().message)
        ke_spv = Notification.objects.get(user=self.spv)
        self.assertIn("2 pelanggan lama tidak order", ke_spv.message)
        self.assertIn("terlama 90 hari", ke_spv.message)
        self.assertEqual(ke_spv.url, reverse("opportunities:follow_up_pelanggan"))
        self.assertEqual(Notification.objects.filter(user=self.lain).count(), 0)
        # Sinkron berikutnya tanpa pelanggan baru tidak menambah notifikasi.
        self._sinkron(_item("6281234567890", "Budi", 91), _item("6285700001111", "Sari", 71))
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(F.objects.get(nomor="6281234567890").hari_sejak, 91)

    def test_atasan_dimatikan_hanya_pemilik_yang_diberi_tahu(self):
        p = PengaturanFollowUp.ambil()
        p.kirim_ke_atasan = False
        p.save()
        self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70))
        self.assertEqual(Notification.objects.filter(user=self.sales).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.spv).count(), 0)

    def test_pengaturan_mati_tidak_menghubungi_bintang(self):
        p = PengaturanFollowUp.ambil()
        p.aktif = False
        p.save()
        ringkas, m = self._sinkron(_item("6281234567890", "Budi", 90))
        self.assertTrue(ringkas["dilewati"])
        m.assert_not_called()
        self.assertEqual(F.objects.count(), 0)

    def test_ambang_dari_pengaturan_dikirim_ke_bintang(self):
        p = PengaturanFollowUp.ambil()
        p.hari_dorman, p.min_transaksi = 45, 3
        p.save()
        _r, m = self._sinkron()
        m.assert_called_once_with(45, 3)

    def test_ditunda_muncul_lagi_setelah_waktunya(self):
        self._sinkron(_item("6281234567890", "Budi", 90))
        row = F.objects.get(nomor="6281234567890")
        svc.tandai(row, "tunda", self.sales, "nanti", 7)
        self._sinkron(_item("6281234567890", "Budi", 91))
        self.assertEqual(F.objects.get(pk=row.pk).status, F.DITUNDA)
        F.objects.filter(pk=row.pk).update(ditunda_sampai=HARI_INI - datetime.timedelta(days=1))
        ringkas, _m = self._sinkron(_item("6281234567890", "Budi", 98))
        self.assertEqual(ringkas["dibuka_lagi"], 1)
        row.refresh_from_db()
        self.assertEqual((row.status, row.diberitahu_pada is not None), (F.BARU, True))  # diberitahu ulang di sinkron yang sama

    def test_sudah_dihubungi_muncul_lagi_bila_belum_order_setelah_jeda(self):
        self._sinkron(_item("6281234567890", "Budi", 90))
        row = F.objects.get(nomor="6281234567890")
        svc.tandai(row, "dihubungi", self.sales, "dibalas, nanti dipikir")
        self._sinkron(_item("6281234567890", "Budi", 91))
        self.assertEqual(F.objects.get(pk=row.pk).status, F.DIHUBUNGI)
        F.objects.filter(pk=row.pk).update(ditangani_pada=row.ditangani_pada - datetime.timedelta(days=15))
        self._sinkron(_item("6281234567890", "Budi", 105))
        self.assertEqual(F.objects.get(pk=row.pk).status, F.BARU)

    def test_diabaikan_tidak_muncul_lagi(self):
        self._sinkron(_item("6281234567890", "Budi", 90))
        row = F.objects.get(nomor="6281234567890")
        svc.tandai(row, "abaikan", self.sales)
        n_awal = Notification.objects.count()
        self._sinkron(_item("6281234567890", "Budi", 200))
        self.assertEqual(F.objects.get(pk=row.pk).status, F.ABAIKAN)
        self.assertEqual(Notification.objects.count(), n_awal)

    def test_order_lagi_ditandai_kembali_berdasarkan_pemeriksaan_bintang(self):
        self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70))
        # Budi order lagi 2 hari lalu (hilang dari daftar dorman); Sari hilang karena ambang dinaikkan.
        pemeriksaan = {"hasil": [_item("6281234567890", "Budi", 2), _item("6285700001111", "Sari", 70)]}
        with mock.patch.object(bintang_order, "pelanggan_dorman", side_effect=[_jawab(), pemeriksaan]) as m:
            ringkas = svc.sinkron_dorman()
        self.assertEqual(ringkas["kembali"], 1)
        self.assertEqual(m.call_args_list[1].kwargs["nomor"], "6281234567890,6285700001111")
        self.assertEqual(F.objects.get(nomor="6281234567890").status, F.KEMBALI)
        self.assertEqual(F.objects.get(nomor="6285700001111").status, F.BARU)

    def test_daftar_terpotong_tidak_menandai_kembali(self):
        self._sinkron(_item("6281234567890", "Budi", 90))
        with mock.patch.object(bintang_order, "pelanggan_dorman", return_value=_jawab(dipotong=True)) as m:
            svc.sinkron_dorman()
        self.assertEqual(m.call_count, 1)
        self.assertEqual(F.objects.get(nomor="6281234567890").status, F.BARU)

    def test_kembali_lalu_dorman_lagi_dibuka_baru_dan_diberitahu(self):
        self._sinkron(_item("6281234567890", "Budi", 90))
        F.objects.filter(nomor="6281234567890").update(status=F.KEMBALI)
        n = Notification.objects.count()
        self._sinkron(_item("6281234567890", "Budi", 95))
        self.assertEqual(F.objects.get(nomor="6281234567890").status, F.BARU)
        self.assertGreater(Notification.objects.count(), n)

    def test_normalisasi_nomor(self):
        self.assertEqual(svc.normalisasi_nomor("0812-3456-7890"), "6281234567890")
        self.assertEqual(svc.normalisasi_nomor("+62 812 3456 7890"), "6281234567890")
        self.assertEqual(svc.normalisasi_nomor("abc"), "")

    def test_tugas_celery_melewati_saat_bintang_mati(self):
        from horilla_crm.opportunities.tasks import sinkron_follow_up_pelanggan

        with mock.patch.object(bintang_order, "pelanggan_dorman", side_effect=bintang_order.BintangOrderError("mati")):
            hasil = sinkron_follow_up_pelanggan()
        self.assertIn("Dilewati", hasil)
        self.assertEqual(F.objects.count(), 0)

    def test_jadwal_harian_terdaftar(self):
        from horilla_crm.opportunities.celery_schedules import HORILLA_BEAT_SCHEDULE

        entri = HORILLA_BEAT_SCHEDULE["sinkron-follow-up-pelanggan-harian"]
        self.assertEqual(entri["task"], "horilla_crm.opportunities.tasks.sinkron_follow_up_pelanggan")


class HalamanTests(_DasarFollowUp):
    def setUp(self):
        super().setUp()
        self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70, total=100000))
        self.budi = F.objects.get(nomor="6281234567890")
        self.sari = F.objects.get(nomor="6285700001111")
        self.url = reverse("opportunities:follow_up_pelanggan")

    def _buka(self, user, **params):
        self._as(user)
        return self.client.get(self.url, params, secure=True, follow=True)

    def test_staff_hanya_melihat_pelanggan_miliknya(self):
        html = self._buka(self.sales).content.decode()
        self.assertIn("Budi", html)
        self.assertNotIn("Sari", html)
        self.assertNotIn("Sinkron sekarang", html)
        self.assertIn("https://wa.me/6281234567890?text=", html)

    def test_atasan_melihat_semua_dan_pengaturan(self):
        html = self._buka(self.spv).content.decode()
        self.assertIn("Budi", html)
        self.assertIn("Sari", html)
        self.assertIn("Sinkron sekarang", html)

    def test_tanpa_izin_ditolak(self):
        tamu = self._user("tamu.uji", [])
        res = self._buka(tamu)
        self.assertNotIn("Budi", res.content.decode())

    def test_staff_tidak_bisa_mengubah_pelanggan_orang_lain(self):
        self._as(self.sales)
        res = self.client.post(reverse("opportunities:follow_up_aksi", args=[self.sari.pk, "abaikan"]), **H)
        self.assertEqual(res.status_code, 404)
        self.sari.refresh_from_db()
        self.assertEqual(self.sari.status, F.BARU)

    def test_aksi_dihubungi_dengan_catatan_dan_tunda(self):
        self._as(self.sales)
        url = reverse("opportunities:follow_up_aksi", args=[self.budi.pk, "dihubungi"])
        res = self.client.post(url, HTTP_HX_PROMPT="minta penawaran banner", **H)
        self.assertEqual(res.status_code, 200)
        self.budi.refresh_from_db()
        self.assertEqual((self.budi.status, self.budi.catatan, self.budi.ditangani_oleh_id), (F.DIHUBUNGI, "minta penawaran banner", self.sales.pk))
        res = self.client.post(reverse("opportunities:follow_up_aksi", args=[self.budi.pk, "tunda"]), {"hari": 14}, **H)
        self.budi.refresh_from_db()
        self.assertEqual((self.budi.status, self.budi.ditunda_sampai), (F.DITUNDA, HARI_INI + datetime.timedelta(days=14)))
        res = self.client.post(reverse("opportunities:follow_up_aksi", args=[self.budi.pk, "tunda"]), {"hari": 3}, **H)
        self.assertIn("tidak valid", res.content.decode())
        res = self.client.post(reverse("opportunities:follow_up_aksi", args=[self.budi.pk, "buka"]), **H)
        self.budi.refresh_from_db()
        self.assertEqual(self.budi.status, F.BARU)

    def test_pengaturan_hanya_pengelola_dan_divalidasi(self):
        url = reverse("opportunities:follow_up_pengaturan")
        isi = {"aktif": "on", "hari_dorman": "45", "min_transaksi": "2", "jeda_ulang_hari": "10", "kirim_ke_atasan": "on"}
        self._as(self.sales)
        self.client.post(url, isi, **H)
        self.assertEqual(PengaturanFollowUp.ambil().hari_dorman, 60)
        self._as(self.spv)
        self.client.post(url, isi, **H)
        p = PengaturanFollowUp.ambil()
        self.assertEqual((p.hari_dorman, p.min_transaksi, p.jeda_ulang_hari), (45, 2, 10))
        res = self.client.post(url, {**isi, "hari_dorman": "3"}, **H)
        self.assertIn("antara 7 dan 1100", res.content.decode())
        self.assertEqual(PengaturanFollowUp.ambil().hari_dorman, 45)

    def test_sinkron_manual_hanya_pengelola_dan_menampilkan_galat(self):
        url = reverse("opportunities:follow_up_sinkron")
        self._as(self.sales)
        with mock.patch.object(bintang_order, "pelanggan_dorman") as m:
            self.client.post(url, **H)
        m.assert_not_called()
        self._as(self.spv)
        with mock.patch.object(bintang_order, "pelanggan_dorman", side_effect=bintang_order.BintangOrderError("Bintang tidak bisa dihubungi.")):
            res = self.client.post(url, **H)
        self.assertIn("Bintang tidak bisa dihubungi.", res.content.decode())


class DasborTests(_DasarFollowUp):
    RINGKASAN = {"omzet": 12500000, "dibayar": 9000000, "belum_dibayar": 3500000, "transaksi": 40}

    def _kpi(self, user):
        gen = DefaultDashboardGenerator(user, self.company, date_range=30)
        return {k["title"]: k for k in gen.generate_kpi_data()}

    def test_atasan_melihat_omzet_keseluruhan_di_dasbor(self):
        with mock.patch.object(bintang_order, "laporan_penjualan", return_value={"ringkasan": self.RINGKASAN}) as m:
            kpi = self._kpi(self.spv)
        self.assertEqual(kpi["Omzet Keseluruhan"]["value"], "Rp 12.500.000")
        self.assertEqual(kpi["Omzet Sudah Dibayar"]["value"], "Rp 9.000.000")
        self.assertEqual(kpi["Omzet Belum Dibayar"]["value"], "Rp 3.500.000")
        self.assertIn(reverse("opportunities:laporan_sales"), kpi["Omzet Keseluruhan"]["url"])
        mulai, selesai = m.call_args.args
        self.assertEqual((selesai, (selesai - mulai).days), (HARI_INI, 30))

    def test_omzet_di_cache_dan_tidak_dipanggil_ulang(self):
        with mock.patch.object(bintang_order, "laporan_penjualan", return_value={"ringkasan": self.RINGKASAN}) as m:
            self._kpi(self.spv)
            self._kpi(self.spv)
        self.assertEqual(m.call_count, 1)

    def test_staff_tidak_melihat_omzet_keseluruhan(self):
        with mock.patch.object(bintang_order, "laporan_penjualan", return_value={"ringkasan": self.RINGKASAN}) as m:
            kpi = self._kpi(self.sales)
        self.assertNotIn("Omzet Keseluruhan", kpi)
        m.assert_not_called()

    def test_bintang_mati_dasbor_tetap_tampil(self):
        with mock.patch.object(bintang_order, "laporan_penjualan", side_effect=bintang_order.BintangOrderError("mati")) as m:
            kpi = self._kpi(self.spv)
            self._kpi(self.spv)
        self.assertEqual(kpi["Omzet Keseluruhan"]["value"], "Tidak bisa dimuat")
        self.assertEqual(m.call_count, 1)  # kegagalan di-cache sebentar, dasbor tidak menunggu terus

    def test_kpi_follow_up_menghitung_sesuai_hak_lihat(self):
        self._sinkron(_item("6281234567890", "Budi", 90), _item("6285700001111", "Sari", 70))
        with mock.patch.object(bintang_order, "laporan_penjualan", return_value={"ringkasan": self.RINGKASAN}):
            self.assertEqual(self._kpi(self.spv)["Pelanggan Perlu Follow Up"]["value"], 2)
            self.assertEqual(self._kpi(self.sales)["Pelanggan Perlu Follow Up"]["value"], 1)
            self.assertEqual(self._kpi(self.lain)["Pelanggan Perlu Follow Up"]["value"], 0)

    def test_periode_semua_dibatasi_tiga_tahun(self):
        gen = DefaultDashboardGenerator(self.spv, self.company, date_range=None)
        from horilla_crm.opportunities.dashboard import _periode_omzet

        mulai, selesai = _periode_omzet(gen)
        self.assertEqual((selesai - mulai).days, 1099)
