"""Sinkron ganti sandi HR <-> ERP <-> CRM (2026-09-30).

HR = pusat. Sandi akun CRM berubah -> dikirim (sebagai HASH, bukan sandi asli) ke HR,
yang menerapkannya ke akun HR/mobile lalu meneruskan ke ERP. Penerima dari HR
menerapkan tanpa memicu pengiriman balik. Gagal menghubungi HR tidak menggagalkan
penggantian sandi; cuma dicatat di log.
"""
import logging
import os

import requests
from django.contrib.auth.hashers import identify_hasher
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

DEFAULT_HR_SANDI_URL = "http://horilla-hr-web-1:8000/api/auth/sinkron-sandi/"
DEFAULT_HR_HOST = "hr.starphotoadvertising.com"
MODEL = "core.HorillaUser"


def hash_valid(encoded):
    if not encoded or not isinstance(encoded, str) or encoded.startswith("!"):
        return False
    try:
        identify_hasher(encoded)
    except ValueError:
        return False
    return True


def terapkan_hash(user, encoded):
    """Salin hash dari HR tanpa memicu pengiriman balik."""
    user.password = encoded
    user._tanpa_sinkron_sandi = True
    user.save(update_fields=["password"])


def kirim_ke_hr(hr_employee_id, encoded):
    api_key = os.getenv("INSIGHTS_BRIDGE_API_KEY")
    if not api_key:
        return
    headers = {"X-Api-Key": api_key, "X-Forwarded-Proto": "https", "Host": os.getenv("HR_HOST", DEFAULT_HR_HOST)}
    try:
        r = requests.post(
            os.getenv("HR_SANDI_URL", DEFAULT_HR_SANDI_URL),
            json={"hr_employee_id": hr_employee_id, "password_hash": encoded, "sumber": "crm"},
            headers=headers, timeout=5,
        )
        r.raise_for_status()
    except Exception:
        logger.exception("Sinkron sandi CRM->HR gagal untuk hr_employee_id=%s.", hr_employee_id)


@receiver(pre_save, sender=MODEL, dispatch_uid="sandi_pre_save")
def _ingat_sandi_lama(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or not instance.pk or (update_fields is not None and "password" not in update_fields):
        return
    instance._sandi_lama = sender._base_manager.filter(pk=instance.pk).values_list("password", flat=True).first()


@receiver(post_save, sender=MODEL, dispatch_uid="sandi_post_save")
def _teruskan_sandi_baru(sender, instance, created=False, raw=False, **kwargs):
    # pop: atribut tidak boleh tertinggal di objek yang dipakai ulang untuk simpan berikutnya
    lama = instance.__dict__.pop("_sandi_lama", None)
    if raw or created or instance.__dict__.pop("_tanpa_sinkron_sandi", False):
        return
    if lama is None or lama == instance.password or not hash_valid(instance.password):
        return
    if not instance.hr_employee_id:
        return
    hr_id, encoded = instance.hr_employee_id, instance.password
    transaction.on_commit(lambda: kirim_ke_hr(hr_id, encoded))
