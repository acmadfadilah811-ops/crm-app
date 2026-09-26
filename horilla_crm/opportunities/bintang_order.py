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


def tandai_menang(opportunity_id, total=None):
    """Order Bintang dari Opportunity ini sudah lunas -> Opportunity jadi Closed Won.

    Dipanggil oleh jembatan Bintang -> CRM saat order lunas, dan sebagai
    cadangan saat tab Order Bintang dibuka. Idempoten: stage yang sudah won
    tidak disentuh. Nilai amount yang sudah diisi Sales tidak ditimpa.
    Return: True bila diubah, False bila sudah won, None bila tidak ada.
    """
    import datetime
    from decimal import Decimal, InvalidOperation

    from django.db import transaction

    from horilla_crm.opportunities.models import Opportunity, OpportunityStage

    with transaction.atomic():
        opp = Opportunity.all_objects.select_for_update().filter(pk=opportunity_id).first()
        if opp is None:
            return None
        if opp.stage_id and opp.stage.stage_type == "won":
            return False
        won = OpportunityStage.all_objects.filter(stage_type="won")
        stage = won.filter(company_id=opp.company_id).order_by("order").first() or won.order_by("order").first()
        if stage is None:
            logger.error("Tidak ada OpportunityStage stage_type='won'; Opportunity %s tidak diubah.", opp.pk)
            return None
        opp.stage = stage
        opp.close_date = datetime.date.today()
        if not opp.amount:
            try:
                opp.amount = Decimal(str(total or 0))
            except InvalidOperation:
                pass
        opp.save()
        return True
