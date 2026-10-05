"""Sinkron foto profil HR <-> ERP (Bintang) <-> CRM (2026-10-05).

HR = pusat, sama seperti sinkron sandi (sinkron_sandi.py).
- Foto profil akun CRM berubah/dihapus -> dikirim ke HR, HR menerapkannya ke data
  karyawan lalu meneruskan ke ERP.
- Foto dari HR diterapkan lewat queryset.update() sehingga sinyal tidak terpicu
  dan tidak ada pengiriman balik.
Sebelum dikirim foto diperkecil (sisi terpanjang 800 px, JPEG) supaya ringan dan
lolos batas ukuran badan permintaan. Gagal menghubungi HR tidak menggagalkan
penggantian foto; cuma dicatat di log.
"""
import base64
import io
import logging
import os

import requests
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

DEFAULT_HR_FOTO_URL = "http://horilla-hr-web-1:8000/api/auth/sinkron-foto/"
DEFAULT_HR_HOST = "hr.starphotoadvertising.com"
FORMAT_DITERIMA = ("JPEG", "PNG", "WEBP")
MAKS_BYTE = 1024 * 1024
SISI_MAKS = 800


def siapkan_foto(data):
    """Perkecil gambar menjadi JPEG. None bila bukan gambar yang didukung."""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in FORMAT_DITERIMA + ("GIF", "BMP"):
                return None
            img = img.convert("RGB")
            img.thumbnail((SISI_MAKS, SISI_MAKS))
            keluar = io.BytesIO()
            img.save(keluar, format="JPEG", quality=85)
    except Exception:
        return None
    hasil = keluar.getvalue()
    return hasil if len(hasil) <= MAKS_BYTE else None


def foto_valid(data):
    from PIL import Image

    if not data or len(data) > MAKS_BYTE:
        return False
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
            return img.format in FORMAT_DITERIMA
    except Exception:
        return False


def baca_payload_foto(request_data):
    """(ok, data_or_None, pesan_galat). data None = hapus foto."""
    if request_data.get("hapus"):
        return True, None, ""
    try:
        data = base64.b64decode(str(request_data.get("foto") or ""), validate=True)
    except Exception:
        return False, None, "Foto bukan base64 yang valid."
    if not foto_valid(data):
        return False, None, "Foto harus JPEG/PNG/WEBP dan maksimal 1 MB."
    return True, data, ""


def terapkan_foto(user, data):
    """Simpan foto dari HR tanpa memicu sinyal (tidak ada pengiriman balik)."""
    from django.core.files.base import ContentFile

    from horilla.contrib.core.models.user import HorillaUser

    if data is None:
        HorillaUser.objects.filter(pk=user.pk).update(profile=None)
        return
    nama = user.profile.storage.save(f"profil_hr/hr_{user.hr_employee_id}.jpg", ContentFile(data))
    HorillaUser.objects.filter(pk=user.pk).update(profile=nama)


def kirim_ke_hr(hr_employee_id, nama_berkas, storage):
    api_key = os.getenv("INSIGHTS_BRIDGE_API_KEY")
    if not api_key:
        return
    if nama_berkas:
        try:
            with storage.open(nama_berkas, "rb") as f:
                data = siapkan_foto(f.read())
        except Exception:
            logger.exception("Sinkron foto CRM->HR: berkas tidak terbaca (hr_employee_id=%s).", hr_employee_id)
            return
        if data is None:
            logger.warning("Sinkron foto CRM->HR dilewati: berkas bukan gambar yang didukung (hr_employee_id=%s).", hr_employee_id)
            return
        payload = {"hr_employee_id": hr_employee_id, "foto": base64.b64encode(data).decode(), "sumber": "crm"}
    else:
        payload = {"hr_employee_id": hr_employee_id, "hapus": True, "sumber": "crm"}
    headers = {"X-Api-Key": api_key, "X-Forwarded-Proto": "https", "Host": os.getenv("HR_HOST", DEFAULT_HR_HOST)}
    try:
        r = requests.post(os.getenv("HR_FOTO_URL", DEFAULT_HR_FOTO_URL), json=payload, headers=headers, timeout=10)
        r.raise_for_status()
    except Exception:
        logger.exception("Sinkron foto CRM->HR gagal untuk hr_employee_id=%s.", hr_employee_id)


@receiver(pre_save, sender="core.HorillaUser", dispatch_uid="foto_pre_save")
def _ingat_foto_lama(sender, instance, raw=False, update_fields=None, **kwargs):
    if raw or not instance.pk or (update_fields is not None and "profile" not in update_fields):
        return
    instance._foto_lama = sender._base_manager.filter(pk=instance.pk).values_list("profile", flat=True).first() or ""


@receiver(post_save, sender="core.HorillaUser", dispatch_uid="foto_post_save")
def _teruskan_foto_baru(sender, instance, created=False, raw=False, **kwargs):
    # pop: atribut tidak boleh tertinggal di objek yang dipakai ulang untuk simpan berikutnya
    lama = instance.__dict__.pop("_foto_lama", None)
    if raw or created or lama is None or not instance.hr_employee_id:
        return
    baru = instance.profile.name or ""
    if baru == lama:
        return
    hr_id, storage = instance.hr_employee_id, instance.profile.storage
    transaction.on_commit(lambda: kirim_ke_hr(hr_id, baru, storage))
