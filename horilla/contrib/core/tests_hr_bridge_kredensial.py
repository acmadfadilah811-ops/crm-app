"""Jembatan HR -> CRM menerima username & password awal dari HR supaya
kredensial seragam dengan HR/mobile (2026-09-29)."""
import os
from unittest import mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from horilla.contrib.core.models.organization import Role
from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee/"


class HRBridgeKredensialSeragamTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        env = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        env.start()
        self.addCleanup(env.stop)
        spv = Role.objects.create(role_name="SPV Sales Marketing & Creative")
        Role.objects.create(role_name="Tim Sales Marketing & Creative", parent_role=spv)

    def _post(self, **extra):
        payload = {
            "hr_employee_id": 701, "first_name": "Sinta", "last_name": "Marketing",
            "email": "sinta@contoh.com", "job_position": "Tim Sales Marketing & Creative",
            "department": "Sales Marketing & Creative", **extra,
        }
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY="kunci-uji")

    def test_username_dan_password_dari_hr_dipakai(self):
        res = self._post(username="sinta.marketing", password="PasswordAwal1")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data["username"], "sinta.marketing")
        self.assertNotIn("temp_password", res.data)
        self.assertTrue(HorillaUser.objects.get(hr_employee_id=701).check_password("PasswordAwal1"))

    def test_username_terpakai_dijawab_409(self):
        HorillaUser.objects.create(username="sinta.marketing")
        res = self._post(username="sinta.marketing", password="PasswordAwal1")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)
        self.assertTrue(res.data["username_terpakai"])
        self.assertFalse(HorillaUser.objects.filter(hr_employee_id=701).exists())

    def test_password_terlalu_pendek_ditolak(self):
        res = self._post(username="sinta.marketing", password="123")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tanpa_username_password_tetap_pakai_cara_lama(self):
        res = self._post()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertIn("temp_password", res.data)
