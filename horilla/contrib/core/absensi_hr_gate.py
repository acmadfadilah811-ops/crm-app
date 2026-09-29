"""Gerbang absensi HR untuk CRM (2026-09-29).

Keputusan user: HR (Horilla HR mobile/web) satu-satunya sumber absensi;
karyawan yang belum absen masuk -- atau sudah absen pulang -- tidak bisa
membuka CRM sama sekali. Pasangan dari api/services/absensi_hr_gate.py di
Bintang (logika & pesan dibuat sama).

- Superuser (owner/admin CRM) selalu bebas.
- Status diambil dari HR /api/attendance/status-absensi/ (X-Api-Key =
  INSIGHTS_BRIDGE_API_KEY), di-cache 60 detik per karyawan.
- HR tidak bisa dihubungi -> fail-open (boleh), dicatat di log.
- Saklar env ABSENSI_HR_GATE_AKTIF (default mati) -- dimatikan darurat
  tanpa deploy ulang; selalu mati saat `manage.py test`.
"""

import logging
import os
import sys
from dataclasses import dataclass

import requests
from django.contrib import messages
from django.contrib.auth import logout
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://horilla-hr-web-1:8000/api/attendance/status-absensi/"
DEFAULT_HOST = "hr.starphotoadvertising.com"
TIMEOUT = 3
CACHE_DETIK = 60
CACHE_DETIK_GAGAL = 20

# Tetap bisa diakses walau terkunci (login, lupa password, aset, jembatan
# server-ke-server yang pakai API key, bukan sesi pengguna).
AWALAN_DIKECUALIKAN = (
    "/login", "/logout", "/forgot-password", "/reset-password",
    "/static/", "/media/", "/api/", "/health", "/favicon",
)


@dataclass(frozen=True)
class HasilGerbang:
    boleh: bool
    status: str
    pesan: str = ""


def gerbang_aktif():
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        return os.getenv("ABSENSI_HR_GATE_AKTIF_TEST", "False") == "True"
    return os.getenv("ABSENSI_HR_GATE_AKTIF", "False") == "True"


def _tanya_hr(hr_employee_id):
    api_key = os.getenv("INSIGHTS_BRIDGE_API_KEY")
    if not api_key:
        logger.warning("INSIGHTS_BRIDGE_API_KEY belum diisi -- gerbang absensi HR CRM dilewati.")
        return None
    headers = {
        "X-Api-Key": api_key,
        "X-Forwarded-Proto": "https",
        "Host": os.getenv("HR_HOST", DEFAULT_HOST),
    }
    try:
        res = requests.get(
            os.getenv("HR_STATUS_ABSENSI_URL", DEFAULT_URL),
            params={"hr_employee_id": hr_employee_id}, headers=headers, timeout=TIMEOUT,
        )
        res.raise_for_status()
        return res.json()
    except Exception:
        logger.exception("Gagal cek status absensi HR hr_employee_id=%s (fail-open).", hr_employee_id)
        return None


def _status_hr(hr_employee_id, pakai_cache=True):
    kunci = f"absen_hr:{hr_employee_id}"
    if pakai_cache:
        tersimpan = cache.get(kunci)
        if tersimpan is not None:
            return tersimpan
    data = _tanya_hr(hr_employee_id)
    # Cuma status "masuk" (dan HR tidak tersedia) yang di-cache: status
    # terkunci selalu dicek ulang, supaya karyawan yang baru absen di HP
    # langsung bisa masuk tanpa menunggu cache habis.
    if data is None:
        data = {"hr_tidak_tersedia": True}
        cache.set(kunci, data, CACHE_DETIK_GAGAL)
    elif data.get("status") == "masuk":
        cache.set(kunci, data, CACHE_DETIK)
    return data


def cek_gerbang(user, pakai_cache=True):
    if not gerbang_aktif() or not getattr(user, "is_authenticated", False) or user.is_superuser:
        return HasilGerbang(True, "bebas")

    hr_employee_id = getattr(user, "hr_employee_id", None)
    if not hr_employee_id:
        return HasilGerbang(
            False, "tidak_terhubung",
            "Akun Anda belum terhubung ke data karyawan HR, jadi absensi tidak bisa dicek. "
            "Hubungi HR/admin.",
        )

    data = _status_hr(hr_employee_id, pakai_cache=pakai_cache)
    if data.get("hr_tidak_tersedia"):
        return HasilGerbang(True, "hr_tidak_tersedia")
    if not data.get("applicable"):
        return HasilGerbang(False, "tidak_terhubung", "Data karyawan Anda tidak ditemukan atau nonaktif di HR. Hubungi HR.")
    if data.get("status") == "masuk":
        return HasilGerbang(True, "masuk")
    if data.get("status") == "pulang":
        return HasilGerbang(
            False, "pulang",
            f"Anda sudah absen pulang di HR hari ini (pukul {(data.get('jam_pulang') or '')[:5]}). "
            "CRM terkunci sampai absen masuk berikutnya.",
        )
    return HasilGerbang(
        False, "belum",
        "Anda belum absen masuk hari ini. Absen masuk dulu di aplikasi HR (HP) atau web HR, lalu login lagi.",
    )


class AbsensiHRGateMiddleware:
    """Keluarkan pengguna yang belum absen masuk / sudah absen pulang di HR,
    lalu arahkan ke halaman login dengan pesan alasannya."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if (
            user is not None
            and user.is_authenticated
            and not request.path.startswith(AWALAN_DIKECUALIKAN)
        ):
            hasil = cek_gerbang(user)
            if not hasil.boleh:
                logout(request)
                messages.error(request, hasil.pesan)
                tujuan = "/login/"
                if request.headers.get("HX-Request"):
                    response = HttpResponse(status=204)
                    response["HX-Redirect"] = tujuan
                    return response
                return redirect(tujuan)
        return self.get_response(request)
