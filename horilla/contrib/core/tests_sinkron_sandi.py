"""Ganti sandi CRM <-> HR <-> ERP (2026-09-30)."""
import os
from unittest import mock

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from horilla.contrib.core import sinkron_sandi as svc
from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee-sandi/"


class KirimKeHrCrmTests(TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ, {"INSIGHTS_BRIDGE_API_KEY": "kunci-insights"})
        env.start()
        self.addCleanup(env.stop)
        self.user = HorillaUser.objects.create(username="crm.sandi", hr_employee_id=960)
        self.user.set_password("lama12345")
        self.user.save()

    def _ganti(self, **atribut):
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                self.user.set_password("Baru12345678")
                for k, v in atribut.items():
                    setattr(self.user, k, v)
                self.user.save()
        return post

    def test_ganti_sandi_mengirim_hash_ke_hr_dengan_sumber_crm(self):
        post = self._ganti()
        post.assert_called_once()
        payload = post.call_args.kwargs["json"]
        self.assertEqual((payload["hr_employee_id"], payload["sumber"]), (960, "crm"))
        self.assertTrue(payload["password_hash"].startswith("pbkdf2_"))
        self.assertNotIn("Baru12345678", str(payload))

    def test_update_last_login_tidak_memicu(self):
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                self.user.save(update_fields=["last_login"])
        post.assert_not_called()

    def test_akun_tanpa_hr_tidak_mengirim(self):
        lokal = HorillaUser.objects.create(username="crm.lokal")
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                lokal.set_password("Baru12345678")
                lokal.save()
        post.assert_not_called()

    def test_hr_gagal_tidak_menggagalkan_ganti_sandi(self):
        with mock.patch.object(svc.requests, "post", side_effect=Exception("putus")):
            with self.captureOnCommitCallbacks(execute=True):
                self.user.set_password("Baru12345678")
                self.user.save()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Baru12345678"))


class TerimaDariHrCrmTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        env = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji", "INSIGHTS_BRIDGE_API_KEY": "kunci-insights"})
        env.start()
        self.addCleanup(env.stop)
        self.user = HorillaUser.objects.create(username="crm.terima", hr_employee_id=961)
        self.user.set_password("lama12345")
        self.user.save()
        self.hash_baru = make_password("DariHr12345")

    def kirim(self, payload, key="kunci-uji"):
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY=key)

    def test_hash_diterapkan_tanpa_kirim_balik(self):
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.kirim({"hr_employee_id": 961, "password_hash": self.hash_baru})
        self.assertEqual(res.status_code, 200, res.content)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("DariHr12345"))
        post.assert_not_called()

    def test_api_key_salah_ditolak(self):
        self.assertEqual(self.kirim({"hr_employee_id": 961, "password_hash": self.hash_baru}, key="x").status_code, 401)

    def test_hash_tidak_valid_ditolak(self):
        for h in ("bukan-hash", "", "!tak-bisa"):
            self.assertEqual(self.kirim({"hr_employee_id": 961, "password_hash": h}).status_code, 400, h)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("lama12345"))

    def test_akun_tanpa_sandi_dan_tak_dikenal_dilewati(self):
        tanpa = HorillaUser.objects.create(username="crm.tanpa", hr_employee_id=962)
        tanpa.set_unusable_password()
        tanpa.save()
        self.assertTrue(self.kirim({"hr_employee_id": 962, "password_hash": self.hash_baru}).data.get("skipped"))
        self.assertTrue(self.kirim({"hr_employee_id": 99999, "password_hash": self.hash_baru}).data.get("skipped"))
