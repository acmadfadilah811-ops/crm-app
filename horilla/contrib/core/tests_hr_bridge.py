"""Uji jembatan HR (Horilla HR) -> CRM: endpoint POST /api/bridge/hr-employee/
yang dipanggil server-ke-server oleh sistem HR untuk auto-provision akun
tim marketing begitu HR membuat karyawan baru/approve rekrutmen."""
import os
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from horilla.contrib.core.models.organization import Role
from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee/"


class HRBridgeAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_tanpa_api_key_dikonfigurasi_di_server_ditolak_500(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("HR_BRIDGE_API_KEY", None)
            response = self.client.post(URL, {"hr_employee_id": 1}, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_api_key_salah_ditolak_401(self):
        with mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-benar"}):
            response = self.client.post(
                URL, {"hr_employee_id": 1}, format="json", HTTP_X_API_KEY="kunci-salah"
            )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class HRBridgeCreateAccountTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.env_patch = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.spv_role = Role.objects.create(role_name="SPV Sales Marketing & Creative")
        self.tim_role = Role.objects.create(role_name="Tim Sales Marketing & Creative", parent_role=self.spv_role)

    def _post(self, payload):
        return self.client.post(URL, payload, format="json", HTTP_X_API_KEY="kunci-uji")

    def test_job_position_tim_marketing_dipetakan_ke_role_yang_benar(self):
        response = self._post({
            "hr_employee_id": 201, "first_name": "Sinta", "last_name": "Marketing",
            "email": "sinta@contoh.com", "job_position": "Tim Sales Marketing & Creative",
            "department": "Sales Marketing & Creative",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertIn("temp_password", response.data)
        user = HorillaUser.objects.get(hr_employee_id=201)
        self.assertEqual(user.role_id, self.tim_role.id)
        self.assertTrue(user.check_password(response.data["temp_password"]))

    def test_departemen_selain_marketing_di_skip_tanpa_buat_akun(self):
        response = self._post({
            "hr_employee_id": 202, "first_name": "Budi", "last_name": "Produksi",
            "job_position": "Kordiv A3", "department": "Digital Printing",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("skipped"))
        self.assertFalse(HorillaUser.objects.filter(hr_employee_id=202).exists())

    def test_panggilan_kedua_hr_employee_id_sama_update_bukan_duplikat(self):
        self._post({
            "hr_employee_id": 203, "first_name": "Dedi", "last_name": "Marketing",
            "job_position": "Tim Sales Marketing & Creative", "department": "Sales Marketing & Creative",
        })
        response2 = self._post({
            "hr_employee_id": 203, "first_name": "Dedi", "last_name": "Marketing",
            "job_position": "SPV Sales Marketing & Creative", "department": "Sales Marketing & Creative",
        })
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertFalse(response2.data.get("created"))
        self.assertNotIn("temp_password", response2.data)
        self.assertEqual(HorillaUser.objects.filter(hr_employee_id=203).count(), 1)
        user = HorillaUser.objects.get(hr_employee_id=203)
        self.assertEqual(user.role_id, self.spv_role.id)

    def test_field_wajib_hr_employee_id_kosong_ditolak_400(self):
        response = self._post({"first_name": "Tanpa", "last_name": "Id"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class HRBridgeSetStatusTests(TestCase):
    """AKS-13 (lanjutan, 2026-09-22): POST /api/bridge/hr-employee-status/
    -- HR memanggil ini saat karyawan tim marketing diarsipkan/diaktifkan
    kembali, supaya akun login CRM yang tertaut ikut nonaktif/aktif."""

    URL_STATUS = "/api/bridge/hr-employee-status/"

    def setUp(self):
        self.client = APIClient()
        self.env_patch = mock.patch.dict(os.environ, {"HR_BRIDGE_API_KEY": "kunci-uji"})
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.role = Role.objects.create(role_name="Tim Sales Marketing & Creative")
        self.user = HorillaUser.objects.create_user(
            username="sinta_status_bridge", password="pw12345",
            hr_employee_id=301, role=self.role, is_active=True,
        )

    def _post_status(self, payload, api_key="kunci-uji"):
        return self.client.post(self.URL_STATUS, payload, format="json", HTTP_X_API_KEY=api_key)

    def test_nonaktifkan_akun_lewat_hr_employee_id(self):
        response = self._post_status({"hr_employee_id": 301, "is_active": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_aktifkan_kembali_akun_lewat_hr_employee_id(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        response = self._post_status({"hr_employee_id": 301, "is_active": True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_hr_employee_id_tidak_ditemukan_skip_bukan_error(self):
        response = self._post_status({"hr_employee_id": 99999, "is_active": False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data.get("skipped"))

    def test_tanpa_is_active_400(self):
        response = self._post_status({"hr_employee_id": 301})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_key_salah_ditolak_401(self):
        response = self._post_status({"hr_employee_id": 301, "is_active": False}, api_key="salah")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
