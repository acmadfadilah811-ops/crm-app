"""Metrik KPI CRM untuk capaian otomatis di HR + kartu "KPI Saya" di beranda CRM (2026-11-02)."""

import datetime
from unittest import mock

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.core.cache import cache
from django.test import TestCase
from login_history.models import post_login, post_logout

from horilla.contrib.core.models.user import HorillaUser


def _owner(username):
    return HorillaUser.objects.create(username=username, email=f"{username}@test.horilla")


@mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
class MetrikKpiCrmTests(TestCase):
    headers = {"HTTP_X_API_KEY": "kunci-benar"}

    def setUp(self):
        from horilla_crm.opportunities.models import OpportunityStage

        self.hari_ini = datetime.date.today()
        self.won, _ = OpportunityStage.objects.get_or_create(
            name="Uji KPI Won", defaults={"order": 90, "stage_type": "won", "probability": 100},
        )
        self.open, _ = OpportunityStage.objects.get_or_create(
            name="Uji KPI Open", defaults={"order": 91, "stage_type": "open", "probability": 30},
        )
        self.sales = _owner("sales.kpi")
        self.lain = _owner("lain.kpi")

    def _opp(self, nama, owner, stage, amount, close_date=None):
        from horilla_crm.opportunities.models import Opportunity

        return Opportunity.objects.create(
            name=nama, owner=owner, stage=stage, amount=amount, close_date=close_date,
        )

    def _get(self, **params):
        base = {
            "email": "sales.kpi@test.horilla",
            "dari": (self.hari_ini - datetime.timedelta(days=7)).isoformat(),
            "sampai": self.hari_ini.isoformat(),
        }
        return self.client.get("/api/insights/crm/metrik-kpi/", {**base, **params}, **self.headers)

    def test_tanpa_kunci_ditolak(self):
        res = self.client.get("/api/insights/crm/metrik-kpi/", {"email": "x@y.z"})
        self.assertEqual(res.status_code, 401)

    def test_parameter_tidak_valid(self):
        self.assertEqual(self._get(dari="bukan-tanggal").status_code, 400)
        self.assertEqual(self._get(email="").status_code, 400)

    def test_hanya_peluang_menang_milik_karyawan_di_periode(self):
        self._opp("Menang 1", self.sales, self.won, 3000000, self.hari_ini)
        self._opp("Menang 2", self.sales, self.won, 2000000, self.hari_ini - datetime.timedelta(days=2))
        self._opp("Menang lama", self.sales, self.won, 9000000, self.hari_ini - datetime.timedelta(days=60))
        self._opp("Masih terbuka", self.sales, self.open, 7000000, self.hari_ini)
        self._opp("Milik orang lain", self.lain, self.won, 5000000, self.hari_ini)
        res = self._get()
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual((res.data["peluang_menang"], res.data["omzet_menang"]), (2, 5000000))

    def test_tanpa_close_date_memakai_tanggal_ubah_terakhir(self):
        self._opp("Menang tanpa tanggal", self.sales, self.won, 1500000, None)
        res = self._get()
        self.assertEqual((res.data["peluang_menang"], res.data["omzet_menang"]), (1, 1500000))


@mock.patch.dict("os.environ", {"INSIGHTS_BRIDGE_API_KEY": "kunci-benar"})
class KartuKpiSayaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # django-login-history membaca request.META["HTTP_USER_AGENT"] saat login; klien tes tidak
        # mengirimnya, jadi sinyalnya dilepas selama kelas ini (pola sama dengan field_requirements/tests.py).
        user_logged_in.disconnect(post_login)
        user_logged_out.disconnect(post_logout)

    @classmethod
    def tearDownClass(cls):
        user_logged_in.connect(post_login)
        user_logged_out.connect(post_logout)
        super().tearDownClass()

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        self.user = _owner("kartu.kpi")
        self.user.set_password("x")
        self.user.save()
        self.client.force_login(self.user)

    def _respons(self, status_code=200, data=None):
        jawaban = mock.Mock(status_code=status_code)
        jawaban.json.return_value = data or {}
        jawaban.raise_for_status.return_value = None
        return jawaban

    def test_menampilkan_objektif_dan_key_result(self):
        data = {
            "ditemukan": True,
            "ringkasan": {"total_objektif": 1, "rata_rata_progres": 40},
            "objektif": [{
                "judul": "Target November", "progres": 40, "mulai": "2026-11-01", "selesai": "2026-11-30",
                "key_results": [{"judul": "Peluang menang", "target": 10, "capaian": 4, "progres": 40, "otomatis": True, "satuan": "#"}],
            }],
        }
        with mock.patch("horilla.contrib.dashboard.views.kpi_saya.requests.get", return_value=self._respons(data=data)) as get:
            res = self.client.get("/kpi-saya/")
        self.assertEqual(res.status_code, 200)
        isi = res.content.decode()
        self.assertIn("Target November", isi)
        self.assertIn("4 / 10", isi)
        self.assertEqual(get.call_args.kwargs["params"], {"email": "kartu.kpi@test.horilla"})

    def test_karyawan_hr_tidak_ditemukan(self):
        with mock.patch("horilla.contrib.dashboard.views.kpi_saya.requests.get", return_value=self._respons(404)):
            res = self.client.get("/kpi-saya/")
        self.assertIn("belum terhubung", res.content.decode())

    def test_butuh_login(self):
        self.client.logout()
        self.assertNotEqual(self.client.get("/kpi-saya/").status_code, 200)
