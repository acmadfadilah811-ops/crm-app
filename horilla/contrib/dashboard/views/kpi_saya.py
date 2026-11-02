"""Kartu "KPI Saya" di beranda CRM (2026-11-02).

Target KPI/OKR diisi manager di HR; capaian otomatisnya dihitung HR dari data ERP dan CRM.
Kartu ini hanya menampilkan hasilnya untuk user yang login dan menyegarkan diri tiap 30 detik
(lihat templates/home/kpi_saya.html), jadi angka ikut berubah setelah tugas diselesaikan.
"""
import logging
import os

import requests
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import render
from django.views import View

logger = logging.getLogger(__name__)

DEFAULT_HR_KPI_URL = "http://horilla-hr-web-1:8000/api/insights/hr/kpi-karyawan/"
DEFAULT_HR_HOST = "hr.starphotoadvertising.com"
CACHE_DETIK = 15


def ambil_kpi_dari_hr(email):
    """Return (data, pesan). `data` None bila HR tidak bisa ditanya atau karyawan tidak ditemukan."""
    api_key = os.getenv("INSIGHTS_BRIDGE_API_KEY")
    if not api_key:
        return None, "Jembatan KPI belum dikonfigurasi."
    kunci = f"kpi_saya:{email.lower()}"
    tersimpan = cache.get(kunci)
    if tersimpan is not None:
        return tersimpan, ""
    try:
        res = requests.get(
            os.getenv("HR_KPI_URL", DEFAULT_HR_KPI_URL),
            params={"email": email},
            headers={
                "X-Api-Key": api_key,
                "X-Forwarded-Proto": "https",
                "Host": os.getenv("HR_INSIGHTS_HOST", DEFAULT_HR_HOST),
            },
            timeout=8,
        )
        if res.status_code == 404:
            return None, "Akun Anda belum terhubung ke data karyawan HR."
        res.raise_for_status()
        data = res.json()
    except (requests.RequestException, ValueError):
        logger.warning("Gagal mengambil KPI karyawan dari HR.", exc_info=True)
        return None, "KPI belum bisa dimuat dari HR. Coba lagi sebentar."
    cache.set(kunci, data, CACHE_DETIK)
    return data, ""


class KpiSayaView(LoginRequiredMixin, View):
    def get(self, request):
        email = (getattr(request.user, "email", "") or "").strip()
        data, pesan = ambil_kpi_dari_hr(email) if email else (None, "Akun Anda belum punya email.")
        return render(request, "home/kpi_saya.html", {"data": data, "pesan": pesan})
