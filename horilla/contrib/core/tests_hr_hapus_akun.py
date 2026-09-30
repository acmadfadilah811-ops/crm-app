"""Karyawan dihapus di HR -> akun CRM dihapus bersih atau dinonaktifkan (2026-09-30)."""
import os
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from horilla.contrib.core.models.organization import Role
from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee-hapus/"


class HRHapusAkunCrmTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        env = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        env.start()
        self.addCleanup(env.stop)

    def hapus(self, hr_id, key="kunci-uji"):
        return self.client.post(URL, {"hr_employee_id": hr_id}, format="json", HTTP_X_API_KEY=key)

    def akun(self, hr_id, username):
        return HorillaUser.objects.create(
            username=username, email=f"{username}@uji.test", contact_number="0812", hr_employee_id=hr_id,
        )

    def test_api_key_salah_ditolak(self):
        self.akun(801, "crm.satu")
        self.assertEqual(self.hapus(801, key="salah").status_code, 401)
        self.assertTrue(HorillaUser.objects.filter(hr_employee_id=801).exists())

    def test_akun_tak_dikenal_dilewati(self):
        self.assertTrue(self.hapus(99999).data.get("skipped"))

    def test_akun_tanpa_jejak_dihapus_bersih(self):
        self.akun(802, "crm.dua")
        res = self.hapus(802)
        self.assertEqual(res.data["mode"], "hapus", res.data)
        self.assertFalse(HorillaUser.objects.filter(hr_employee_id=802).exists())

    def test_akun_dengan_jejak_dinonaktifkan_dan_data_pribadi_dikosongkan(self):
        user = self.akun(803, "crm.jejak")
        Role.objects.create(role_name="Role Uji Jejak", created_by=user)  # dibuat-oleh -> jejak
        res = self.hapus(803)
        self.assertEqual(res.data["mode"], "nonaktif", res.data)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertFalse(user.has_usable_password())
        self.assertEqual((user.email, user.contact_number), ("", ""))
        self.assertEqual(user.username, "crm.jejak")

    def test_superuser_tidak_dihapus_keras(self):
        user = self.akun(804, "crm.super")
        user.is_superuser = True
        user.save()
        self.assertEqual(self.hapus(804).data["mode"], "nonaktif")
        self.assertTrue(HorillaUser.objects.filter(hr_employee_id=804).exists())
