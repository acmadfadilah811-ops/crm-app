"""Penyatuan kredensial akun lama CRM dengan HR (2026-09-30)."""
import os
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee-kredensial/"


class HRKredensialCrmTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        env = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        env.start()
        self.addCleanup(env.stop)
        self.user = HorillaUser.objects.create(username="spv.salesmarketingcreative", hr_employee_id=911)
        self.user.set_password("lama12345")
        self.user.save()

    def kirim(self, payload, key="kunci-uji"):
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY=key)

    def test_api_key_salah_ditolak(self):
        self.assertEqual(self.kirim({"hr_employee_id": 911, "username": "spv.marketing", "password": "BaruAwal123"}, key="x").status_code, 401)

    def test_hanya_lihat(self):
        self.assertEqual(self.kirim({"hr_employee_id": 911, "hanya_lihat": True}).data["username"], "spv.salesmarketingcreative")

    def test_username_dan_sandi_disamakan(self):
        res = self.kirim({"hr_employee_id": 911, "username": "spv.marketing", "password": "BaruAwal123"})
        self.assertEqual(res.status_code, 200, res.content)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "spv.marketing")
        self.assertTrue(self.user.check_password("BaruAwal123"))

    def test_username_terpakai_409(self):
        HorillaUser.objects.create(username="spv.marketing")
        res = self.kirim({"hr_employee_id": 911, "username": "spv.marketing", "password": "BaruAwal123"})
        self.assertEqual(res.status_code, 409)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("lama12345"))

    def test_akun_nonaktif_dilewati(self):
        HorillaUser.objects.filter(pk=self.user.pk).update(is_active=False)
        self.assertTrue(self.kirim({"hr_employee_id": 911, "username": "spv.marketing", "password": "BaruAwal123"}).data.get("skipped"))

    def test_sandi_pendek_ditolak(self):
        self.assertEqual(self.kirim({"hr_employee_id": 911, "username": "spv.marketing", "password": "123"}).status_code, 400)

    def test_tak_dikenal_dilewati(self):
        self.assertTrue(self.kirim({"hr_employee_id": 99999, "username": "x.y", "password": "BaruAwal123"}).data.get("skipped"))
