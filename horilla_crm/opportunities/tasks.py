"""Tugas Celery modul opportunities."""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def sinkron_follow_up_pelanggan():
    """Harian: perbarui daftar pelanggan lama tidak order dari Bintang dan kirim notifikasi."""
    from horilla_crm.opportunities import bintang_order as bintang
    from horilla_crm.opportunities.followup import sinkron_dorman

    try:
        ringkas = sinkron_dorman()
    except bintang.BintangOrderError as exc:
        logger.warning("Follow up pelanggan: sinkron dilewati, Bintang tidak terjangkau: %s", exc)
        return f"Dilewati: {exc}"
    logger.info("Follow up pelanggan: %s", ringkas)
    return ringkas
