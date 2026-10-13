"""Follow up pelanggan yang lama tidak order (2026-10-13).

Daftar pelanggan dorman datang dari Bintang (satu-satunya sumber transaksi),
disinkron harian oleh tugas Celery (lihat followup.py). Di sini hanya disimpan
status penanganannya di CRM: siapa pemiliknya, sudah dihubungi/ditunda/diabaikan,
dan kapan terakhir diberi notifikasi. Uang tidak disimpan/dihitung di CRM --
`total_belanja` hanya salinan informasi dari Bintang.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class PengaturanFollowUp(models.Model):
    """Satu baris (pk=1) untuk seluruh CRM."""

    aktif = models.BooleanField(default=True, help_text="Matikan untuk menghentikan sinkron & notifikasi harian.")
    hari_dorman = models.PositiveIntegerField(default=60, help_text="Pelanggan dianggap lama tidak order bila order terakhirnya sudah lewat sekian hari.")
    min_transaksi = models.PositiveIntegerField(default=1, help_text="Hanya pelanggan yang sudah order minimal sekian kali.")
    jeda_ulang_hari = models.PositiveIntegerField(default=14, help_text="Bila pelanggan yang sudah dihubungi masih belum order setelah sekian hari, muncul lagi untuk di-follow up.")
    kirim_ke_atasan = models.BooleanField(default=True, help_text="Atasan (yang melihat semua pelanggan) ikut menerima ringkasan notifikasi.")
    sinkron_terakhir = models.DateTimeField(null=True, blank=True, editable=False)
    sinkron_hasil = models.CharField(max_length=255, blank=True, default="", editable=False)

    class Meta:
        app_label = "opportunities"

    def clean(self):
        if not 7 <= (self.hari_dorman or 0) <= 1100:
            raise ValidationError("Batas hari lama tidak order harus antara 7 dan 1100.")
        if not 1 <= (self.min_transaksi or 0) <= 100:
            raise ValidationError("Minimal transaksi harus antara 1 dan 100.")
        if not 1 <= (self.jeda_ulang_hari or 0) <= 365:
            raise ValidationError("Jeda muncul lagi harus antara 1 dan 365 hari.")

    @classmethod
    def ambil(cls):
        return cls.objects.get_or_create(pk=1)[0]


class PelangganFollowUp(models.Model):
    BARU, DIHUBUNGI, DITUNDA, ABAIKAN, KEMBALI = "baru", "dihubungi", "ditunda", "abaikan", "kembali"
    STATUS = [
        (BARU, "Perlu follow up"),
        (DIHUBUNGI, "Sudah dihubungi"),
        (DITUNDA, "Ditunda"),
        (ABAIKAN, "Diabaikan"),
        (KEMBALI, "Sudah order lagi"),
    ]

    nomor = models.CharField(max_length=20, unique=True, help_text="Nomor HP/WA ternormalisasi (62...).")
    nama = models.CharField(max_length=150, blank=True, default="")
    contact = models.ForeignKey(
        "contacts.Contact", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    pemilik = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        help_text="Pemilik Contact di CRM. Kosong = hanya atasan yang melihat.",
    )
    terakhir_order = models.DateField(null=True, blank=True)
    hari_sejak = models.PositiveIntegerField(default=0)
    jumlah_transaksi = models.PositiveIntegerField(default=0)
    total_belanja = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    status = models.CharField(max_length=12, choices=STATUS, default=BARU, db_index=True)
    ditunda_sampai = models.DateField(null=True, blank=True)
    catatan = models.CharField(max_length=255, blank=True, default="")
    ditangani_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    ditangani_pada = models.DateTimeField(null=True, blank=True)
    diberitahu_pada = models.DateTimeField(null=True, blank=True)
    dibuat = models.DateTimeField(auto_now_add=True)
    diubah = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "opportunities"
        ordering = ["-total_belanja", "nomor"]

    def __str__(self):
        return f"{self.nama or self.nomor} ({self.get_status_display()})"
