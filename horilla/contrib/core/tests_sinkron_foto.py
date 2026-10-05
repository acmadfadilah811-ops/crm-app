"""Sinkron foto profil CRM <-> HR <-> ERP (2026-10-05)."""
import base64
import io
import os
import shutil
import tempfile
from unittest import mock

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from horilla.contrib.core import sinkron_foto as svc
from horilla.contrib.core.models.user import HorillaUser

URL = "/api/bridge/hr-employee-foto/"


def gambar(fmt="PNG", ukuran=(1600, 1200)):
    buf = io.BytesIO()
    Image.new("RGB", ukuran, (30, 30, 200)).save(buf, format=fmt)
    return buf.getvalue()


class _MediaSementara(TestCase):
    def setUp(self):
        cache.clear()
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        ov = override_settings(MEDIA_ROOT=self.media)
        ov.enable()
        self.addCleanup(ov.disable)
        env = mock.patch.dict(os.environ, {"INSIGHTS_BRIDGE_API_KEY": "kunci-insights", "HR_BRIDGE_API_KEY": "kunci-uji"})
        env.start()
        self.addCleanup(env.stop)


class KirimFotoKeHrCrmTests(_MediaSementara):
    def setUp(self):
        super().setUp()
        self.user = HorillaUser.objects.create(username="crm.foto", hr_employee_id=980)

    def _simpan(self, **atribut):
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                for k, v in atribut.items():
                    setattr(self.user, k, v)
                self.user.save()
        return post

    def test_ganti_foto_mengirim_jpeg_kecil_dengan_sumber_crm(self):
        post = self._simpan(profile=SimpleUploadedFile("a.png", gambar(), content_type="image/png"))
        post.assert_called_once()
        payload = post.call_args.kwargs["json"]
        self.assertEqual((payload["hr_employee_id"], payload["sumber"]), (980, "crm"))
        with Image.open(io.BytesIO(base64.b64decode(payload["foto"]))) as img:
            self.assertEqual(img.format, "JPEG")
            self.assertLessEqual(max(img.size), svc.SISI_MAKS)

    def test_hapus_foto_mengirim_hapus(self):
        self._simpan(profile=SimpleUploadedFile("a.png", gambar(), content_type="image/png"))
        post = self._simpan(profile=None)
        self.assertEqual(post.call_args.kwargs["json"], {"hr_employee_id": 980, "hapus": True, "sumber": "crm"})

    def test_simpan_lain_dan_akun_tanpa_hr_tidak_mengirim(self):
        post = self._simpan(first_name="Baru")
        post.assert_not_called()
        lokal = HorillaUser.objects.create(username="crm.lokal")
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                lokal.profile = SimpleUploadedFile("a.png", gambar(), content_type="image/png")
                lokal.save()
        post.assert_not_called()


class TerimaFotoDariHrCrmTests(_MediaSementara):
    def setUp(self):
        super().setUp()
        self.user = HorillaUser.objects.create(username="crm.terima.foto", hr_employee_id=981)

    def kirim(self, payload, key="kunci-uji"):
        return APIClient().post(URL, payload, format="json", HTTP_X_API_KEY=key)

    def test_foto_diterapkan_tanpa_kirim_balik(self):
        data = gambar("JPEG", (300, 300))
        with mock.patch.object(svc.requests, "post") as post:
            with self.captureOnCommitCallbacks(execute=True):
                res = self.kirim({"hr_employee_id": 981, "foto": base64.b64encode(data).decode()})
        self.assertEqual(res.status_code, 200, res.content)
        self.user.refresh_from_db()
        with self.user.profile.open("rb") as f:
            self.assertEqual(f.read(), data)
        post.assert_not_called()

    def test_hapus_dan_validasi(self):
        self.kirim({"hr_employee_id": 981, "foto": base64.b64encode(gambar("JPEG", (50, 50))).decode()})
        self.assertEqual(self.kirim({"hr_employee_id": 981, "hapus": True}).status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile)
        self.assertEqual(self.kirim({"hr_employee_id": 981, "foto": base64.b64encode(b"teks").decode()}).status_code, 400)
        foto = base64.b64encode(gambar("JPEG", (50, 50))).decode()
        self.assertEqual(self.kirim({"hr_employee_id": 981, "foto": foto}, key="x").status_code, 401)
        self.assertTrue(self.kirim({"hr_employee_id": 99999, "foto": foto}).data.get("skipped"))
