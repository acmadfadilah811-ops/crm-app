"""Jembatan HR -> CRM: Departemen -> Department, Jabatan -> Role (2026-09-30)."""
import os
from unittest import mock

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from horilla.contrib.core.models.organization import Department, Role

URL = "/api/bridge/hr-organisasi/"
DEPT = "Sales Marketing & Creative"


class HROrganisasiCrmTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        env = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        env.start()
        self.addCleanup(env.stop)

    def post(self, payload, key="kunci-uji"):
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY=key)

    def test_api_key_salah_ditolak(self):
        self.assertEqual(self.post({"jenis": "departemen", "nama": DEPT}, key="salah").status_code, status.HTTP_401_UNAUTHORIZED)

    def test_departemen_marketing_jadi_department_tanpa_dobel(self):
        self.assertTrue(self.post({"jenis": "departemen", "nama": DEPT}).data["created"])
        self.assertFalse(self.post({"jenis": "departemen", "nama": DEPT}).data["created"])
        self.assertEqual(Department.objects.filter(department_name=DEPT).count(), 1)

    def test_ganti_nama_departemen_lewat_nama_lama(self):
        self.post({"jenis": "departemen", "nama": DEPT})
        self.post({"jenis": "departemen", "nama": DEPT, "nama_lama": DEPT})  # nama sama: tidak error
        self.assertEqual(Department.objects.count(), 1)

    def test_departemen_lain_dilewati(self):
        res = self.post({"jenis": "departemen", "nama": "Digital Printing"})
        self.assertTrue(res.data.get("skipped"))
        self.assertFalse(Department.objects.filter(department_name="Digital Printing").exists())

    def test_jabatan_jadi_role_dengan_induk_spv(self):
        Role.objects.create(role_name=f"SPV {DEPT}")
        res = self.post({"jenis": "jabatan", "nama": "Tim Kreatif", "departemen": DEPT})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        role = Role.objects.get(role_name="Tim Kreatif")
        self.assertEqual(role.parent_role.role_name, f"SPV {DEPT}")

    def test_jabatan_spv_tidak_punya_induk(self):
        res = self.post({"jenis": "jabatan", "nama": f"SPV {DEPT}", "departemen": DEPT})
        self.assertTrue(res.data["created"])
        self.assertIsNone(Role.objects.get(role_name=f"SPV {DEPT}").parent_role)

    def test_jabatan_lama_dengan_nama_sama_tidak_dobel(self):
        Role.objects.create(role_name="Sales")
        self.post({"jenis": "jabatan", "nama": "Sales", "departemen": DEPT})
        self.assertEqual(Role.objects.filter(role_name="Sales").count(), 1)

    def test_ganti_nama_jabatan_mengubah_role_yang_sama(self):
        self.post({"jenis": "jabatan", "nama": "Tim Kreatif", "departemen": DEPT})
        self.post({"jenis": "jabatan", "nama": "Tim Konten", "nama_lama": "Tim Kreatif", "departemen": DEPT})
        self.assertEqual(Role.objects.filter(role_name__in=["Tim Kreatif", "Tim Konten"]).count(), 1)
        self.assertTrue(Role.objects.filter(role_name="Tim Konten").exists())

    def test_jabatan_departemen_lain_dilewati(self):
        res = self.post({"jenis": "jabatan", "nama": "Kordiv A3", "departemen": "Digital Printing"})
        self.assertTrue(res.data.get("skipped"))
        self.assertFalse(Role.objects.filter(role_name="Kordiv A3").exists())
