"""Sinkron & notifikasi follow up pelanggan yang lama tidak order (2026-10-13).

Alur harian (Celery beat, lihat tasks.py):
1. Tanya Bintang siapa yang order terakhirnya sudah lewat `hari_dorman`.
2. Simpan/perbarui PelangganFollowUp; pelanggan baru dorman berstatus "baru".
   Yang ditunda/sudah dihubungi muncul lagi setelah waktunya lewat dan masih belum order.
3. Pelanggan yang sudah order lagi ditandai "kembali" (diperiksa ke Bintang per nomor,
   bukan dari hilangnya nama di daftar, supaya mengubah ambang hari tidak salah menandai).
4. Kirim ringkasan notifikasi: tiap pemilik Contact menerima miliknya, atasan
   (pemegang izin lihat semua Contact) menerima ringkasan seluruhnya.
"""

import logging
import re
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone

from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities.followup_models import PelangganFollowUp as F
from horilla_crm.opportunities.followup_models import PengaturanFollowUp

logger = logging.getLogger(__name__)

IZIN_LIHAT_SEMUA = "contacts.view_contact"
IZIN_LIHAT_SENDIRI = "contacts.view_own_contact"
HARI_TUNDA = (7, 14, 30)


def normalisasi_nomor(raw):
    """Sama dengan normalisasi_nomor_whatsapp di Bintang (08.../62.../+62... dianggap sama)."""
    n = re.sub(r"\D", "", str(raw or ""))
    if n.startswith("0"):
        n = f"62{n[1:]}"
    elif n and not n.startswith("62"):
        n = f"62{n}"
    return n if re.fullmatch(r"\d{8,15}", n) else ""


def _peta_contact():
    from horilla_crm.contacts.models import Contact

    peta = {}
    for c in Contact.all_objects.select_related("contact_owner").order_by("id"):
        for kandidat in (c.contact_number, c.bintang_contact_id):
            n = normalisasi_nomor(kandidat)
            if n and n not in peta:
                peta[n] = c
    return peta


def queryset_untuk(user):
    """Baris yang boleh dilihat: semua bila pemegang izin lihat semua Contact (atasan),
    selain itu hanya milik sendiri."""
    qs = F.objects.select_related("contact", "pemilik", "ditangani_oleh")
    if user.has_perm(IZIN_LIHAT_SEMUA):
        return qs
    if user.has_perm(IZIN_LIHAT_SENDIRI):
        return qs.filter(pemilik=user)
    return qs.none()


def jumlah_perlu_followup(user):
    return queryset_untuk(user).filter(status=F.BARU).count()


def _perbarui_data(row, item, contact):
    row.nama = (item.get("nama") or row.nama or "")[:150]
    row.terakhir_order = date.fromisoformat(item["terakhir"])
    row.hari_sejak = int(item.get("hari_sejak") or 0)
    row.jumlah_transaksi = int(item.get("jumlah_transaksi") or 0)
    row.total_belanja = Decimal(str(item.get("total_belanja") or 0))
    if contact is not None:
        row.contact = contact
        row.pemilik = contact.contact_owner


def _buka_lagi(row):
    row.status = F.BARU
    row.ditunda_sampai = None
    row.diberitahu_pada = None


def _tandai_kembali(rows, ringkas):
    """Tandai 'kembali' baris yang order terakhirnya di Bintang lebih baru dari yang tercatat."""
    if not rows:
        return
    try:
        data = bintang.pelanggan_dorman(7, 1, nomor=",".join(r.nomor for r in rows))
    except bintang.BintangOrderError as exc:
        logger.warning("Follow up: gagal memeriksa pelanggan yang sudah order lagi: %s", exc)
        return
    terbaru = {h["nomor"]: date.fromisoformat(h["terakhir"]) for h in data.get("hasil", [])}
    for row in rows:
        t = terbaru.get(row.nomor)
        if t and row.terakhir_order and t > row.terakhir_order:
            row.status = F.KEMBALI
            row.terakhir_order = t
            row.hari_sejak = (timezone.localdate() - t).days
            row.diberitahu_pada = None
            row.save()
            ringkas["kembali"] += 1


def _kirim_notifikasi(sekarang, kirim_ke_atasan, ringkas):
    from horilla.contrib.core.models.user import HorillaUser
    from horilla.contrib.notifications.methods import create_notification
    from horilla.urls import reverse

    belum = list(F.objects.select_related("pemilik").filter(status=F.BARU, diberitahu_pada__isnull=True))
    if not belum:
        return
    url = reverse("opportunities:follow_up_pelanggan")
    atasan = []
    if kirim_ke_atasan:
        atasan = [
            u for u in HorillaUser.objects.filter(is_active=True, is_superuser=False)
            if u.has_perm(IZIN_LIHAT_SEMUA)
        ]
    atasan_ids = {u.pk for u in atasan}

    def kalimat(baris, awalan=""):
        terlama = max(r.hari_sejak for r in baris)
        return f"{awalan}{len(baris)} pelanggan lama tidak order perlu di-follow up (terlama {terlama} hari)."

    per_pemilik = {}
    for r in belum:
        if r.pemilik_id and r.pemilik.is_active and r.pemilik_id not in atasan_ids:
            per_pemilik.setdefault(r.pemilik_id, (r.pemilik, []))[1].append(r)
    for user, baris in per_pemilik.values():
        if create_notification(user, kalimat(baris), url=url):
            ringkas["notifikasi"] += 1
    for user in atasan:
        if create_notification(user, kalimat(belum), url=url):
            ringkas["notifikasi"] += 1

    F.objects.filter(pk__in=[r.pk for r in belum]).update(diberitahu_pada=sekarang)


def sinkron_dorman(kirim_notifikasi=True):
    """Satu putaran sinkron. Mengembalikan dict ringkasan; BintangOrderError bila Bintang
    tidak terjangkau (pemanggil memutuskan cara menampilkannya)."""
    pengaturan = PengaturanFollowUp.ambil()
    ringkas = {"baru": 0, "dibuka_lagi": 0, "kembali": 0, "notifikasi": 0, "dilewati": False}
    if not pengaturan.aktif:
        ringkas["dilewati"] = True
        return ringkas

    data = bintang.pelanggan_dorman(pengaturan.hari_dorman, pengaturan.min_transaksi)
    sekarang = timezone.now()
    hari_ini = timezone.localdate()
    peta = _peta_contact()
    ada = {r.nomor: r for r in F.objects.all()}
    dalam_daftar = set()

    for item in data.get("hasil", []):
        nomor = item["nomor"]
        dalam_daftar.add(nomor)
        contact = peta.get(nomor)
        row = ada.get(nomor)
        if row is None:
            row = F(nomor=nomor, status=F.BARU)
            _perbarui_data(row, item, contact)
            row.save()
            ringkas["baru"] += 1
            continue

        order_lagi = bool(row.terakhir_order) and date.fromisoformat(item["terakhir"]) > row.terakhir_order
        if order_lagi or row.status == F.KEMBALI:
            _buka_lagi(row)
            row.catatan = ""
            ringkas["baru"] += 1
        elif row.status == F.DITUNDA and row.ditunda_sampai and row.ditunda_sampai <= hari_ini:
            _buka_lagi(row)
            ringkas["dibuka_lagi"] += 1
        elif (
            row.status == F.DIHUBUNGI
            and row.ditangani_pada
            and timezone.localtime(row.ditangani_pada).date() + timedelta(days=pengaturan.jeda_ulang_hari) <= hari_ini
        ):
            _buka_lagi(row)
            ringkas["dibuka_lagi"] += 1
        _perbarui_data(row, item, contact)
        row.save()

    if not data.get("dipotong"):
        _tandai_kembali(
            [r for n, r in ada.items() if n not in dalam_daftar and r.status != F.KEMBALI], ringkas,
        )

    if kirim_notifikasi:
        _kirim_notifikasi(sekarang, pengaturan.kirim_ke_atasan, ringkas)

    pengaturan.sinkron_terakhir = sekarang
    pengaturan.sinkron_hasil = (
        f"{data.get('total', 0)} pelanggan lama tidak order; {ringkas['baru']} baru, "
        f"{ringkas['dibuka_lagi']} muncul lagi, {ringkas['kembali']} sudah order lagi, "
        f"{ringkas['notifikasi']} notifikasi terkirim."
    )[:255]
    pengaturan.save(update_fields=["sinkron_terakhir", "sinkron_hasil"])
    return ringkas


def tandai(row, aksi, user, catatan="", hari=7):
    """Ubah status penanganan satu baris. aksi: dihubungi | tunda | abaikan | buka."""
    sekarang = timezone.now()
    catatan = (catatan or "").strip()[:255]
    if aksi == "dihubungi":
        row.status = F.DIHUBUNGI
    elif aksi == "tunda":
        if hari not in HARI_TUNDA:
            raise ValueError("Pilihan tunda tidak valid.")
        row.status = F.DITUNDA
        row.ditunda_sampai = timezone.localdate() + timedelta(days=hari)
    elif aksi == "abaikan":
        row.status = F.ABAIKAN
    elif aksi == "buka":
        _buka_lagi(row)
    else:
        raise ValueError("Aksi tidak dikenal.")
    if catatan or aksi != "buka":
        row.catatan = catatan or row.catatan
    row.ditangani_oleh = user
    row.ditangani_pada = sekarang
    row.save()
    return row
