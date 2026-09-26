"""Target Sales (2026-09-26, UAT SLS-05/06).

Diinput SPV/Manager di CRM per Sales dengan periode tanggal bebas. Realisasi
tidak disimpan di sini: dihitung dari order Bintang milik Sales tersebut
(jembatan /api/bridge/crm/rekap-sales/), karena uang tercatat di Bintang.
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TargetSales(models.Model):
    sales = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="target_sales")
    nama_periode = models.CharField(max_length=100, help_text="Mis. Oktober 2026, Kuartal IV")
    tanggal_mulai = models.DateField()
    tanggal_selesai = models.DateField()
    target_nilai = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    target_jumlah_order = models.PositiveIntegerField(default=0)
    catatan = models.CharField(max_length=255, blank=True, default="")
    dibuat_oleh = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    dibuat = models.DateTimeField(auto_now_add=True)
    diubah = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "opportunities"
        ordering = ["-tanggal_mulai", "sales__first_name"]

    def clean(self):
        if self.tanggal_mulai and self.tanggal_selesai and self.tanggal_mulai > self.tanggal_selesai:
            raise ValidationError("Tanggal mulai harus sebelum tanggal selesai.")
        if self.tanggal_mulai and self.tanggal_selesai and (self.tanggal_selesai - self.tanggal_mulai).days > 1100:
            raise ValidationError("Periode maksimal 3 tahun.")
        if (self.target_nilai or 0) < 0:
            raise ValidationError("Target nilai tidak boleh negatif.")
        if not (self.target_nilai or 0) and not self.target_jumlah_order:
            raise ValidationError("Isi target nilai, target jumlah order, atau keduanya.")

    def __str__(self):
        return f"{self.sales} - {self.nama_periode}"
