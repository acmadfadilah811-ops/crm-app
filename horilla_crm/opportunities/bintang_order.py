"""Klien jembatan CRM -> Bintang untuk order dari Sales (2026-09-26).

Sales bekerja di CRM saja (tanpa akun Bintang). Dari sebuah Opportunity, Sales
membuat order yang masuk ke Antrean kasir Bintang sebagai draft.
Produk dicari langsung ke katalog Bintang; harga dihitung Bintang dari katalog
(CRM tidak mengirim harga). Auth: X-Api-Key = BINTANG_BRIDGE_API_KEY (kunci
bersama yang sama dengan arah Bintang -> CRM).
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

DEFAULT_URL = "http://backend:8080/api/bridge/crm/"
TIMEOUT = 15


class BintangOrderError(Exception):
    """Pesan yang aman ditampilkan ke Sales."""


def _base():
    return os.getenv("BINTANG_CRM_BRIDGE_URL", DEFAULT_URL).rstrip("/") + "/"


def _headers():
    kunci = os.getenv("BINTANG_BRIDGE_API_KEY")
    if not kunci:
        raise BintangOrderError("Sambungan ke Bintang belum dikonfigurasi. Hubungi admin.")
    return {"X-Api-Key": kunci, "X-Forwarded-Proto": "https"}


def _panggil(metode, jalur, **kwargs):
    try:
        r = requests.request(metode, _base() + jalur, headers=_headers(), timeout=TIMEOUT, **kwargs)
    except requests.RequestException as exc:
        logger.warning("Jembatan CRM->Bintang gagal (%s): %s", jalur, exc)
        raise BintangOrderError("Bintang tidak bisa dihubungi. Coba lagi sebentar lagi.")
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400:
        if r.status_code == 400 and data.get("error"):
            raise BintangOrderError(str(data["error"]))
        logger.warning("Jembatan CRM->Bintang %s menjawab %s", jalur, r.status_code)
        raise BintangOrderError("Bintang menolak permintaan. Hubungi admin.")
    return data


def cari_produk(q):
    return _panggil("GET", "produk/", params={"q": q}).get("hasil", [])


def buat_order(payload):
    return _panggil("POST", "order/", json=payload)


def order_per_opportunity(opportunity_id):
    return _panggil("GET", "order-status/", params={"crm_opportunity_id": opportunity_id}).get("hasil", [])
