"""Halaman Follow Up Pelanggan (2026-10-13): pelanggan yang lama tidak order.

Daftar disinkron harian dari Bintang (lihat horilla_crm/opportunities/followup.py).
Atasan (izin lihat semua Contact) melihat semua baris; staff hanya pelanggan miliknya.
Pengaturan ambang dan sinkron manual hanya untuk pengelola (change_opportunity).
"""

from urllib.parse import quote

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils.html import escape
from django.views import View

from horilla.shortcuts import get_object_or_404, render
from horilla.utils.decorators import method_decorator, permission_required_or_denied
from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities import followup as svc
from horilla_crm.opportunities.followup_models import PelangganFollowUp as F
from horilla_crm.opportunities.followup_models import PengaturanFollowUp
from horilla_crm.opportunities.views.bintang_order import _rp

IZIN_LIHAT = [svc.IZIN_LIHAT_SEMUA, svc.IZIN_LIHAT_SENDIRI]
IZIN_KELOLA = "opportunities.change_opportunity"
MAKS_TAMPIL = 200
TAB = [
    (F.BARU, "Perlu follow up"),
    (F.DIHUBUNGI, "Sudah dihubungi"),
    (F.DITUNDA, "Ditunda"),
    (F.ABAIKAN, "Diabaikan"),
    (F.KEMBALI, "Sudah order lagi"),
]
SALAM = "Halo kak {nama}, sudah lama tidak mampir nih. Ada yang bisa kami bantu untuk kebutuhan cetak berikutnya? 😊"


def _muat_ulang():
    return HttpResponse("<script>window.location.reload();</script>")


def _galat(pesan):
    # Status 200: htmx tidak menukar isi untuk respons 4xx, padahal pesan ini harus tampil.
    return HttpResponse(f'<div class="p-2 text-sm text-red-700">{escape(pesan)}</div>')


class PengaturanForm(forms.ModelForm):
    class Meta:
        model = PengaturanFollowUp
        fields = ["aktif", "hari_dorman", "min_transaksi", "jeda_ulang_hari", "kirim_ke_atasan"]


def _tautan_wa(row):
    nama = (row.nama or "").strip().split(" ")[0] or "kakak"
    return f"https://wa.me/{row.nomor}?text={quote(SALAM.format(nama=nama))}"


@method_decorator(permission_required_or_denied(IZIN_LIHAT), name="dispatch")
class FollowUpPelangganView(LoginRequiredMixin, View):
    template_name = "opportunities/follow_up_pelanggan.html"

    def get(self, request):
        dasar = svc.queryset_untuk(request.user)
        tab = request.GET.get("tab", F.BARU)
        if tab not in dict(TAB):
            tab = F.BARU
        q = (request.GET.get("q") or "").strip()
        jumlah = {r["status"]: r["n"] for r in dasar.values("status").annotate(n=Count("id"))}
        rows = dasar.filter(status=tab)
        if q:
            rows = rows.filter(Q(nama__icontains=q) | Q(nomor__icontains=q))
        rows = list(rows.order_by("-total_belanja", "nomor")[:MAKS_TAMPIL])
        for r in rows:
            r.wa = _tautan_wa(r)
            r.belanja_rp = _rp(r.total_belanja)
        kelola = request.user.has_perm(IZIN_KELOLA)
        pengaturan = PengaturanFollowUp.ambil()
        return render(request, self.template_name, {
            "rows": rows, "tab": tab, "q": q, "kelola": kelola, "pengaturan": pengaturan,
            "tabs": [(k, v, jumlah.get(k, 0)) for k, v in TAB],
            "lihat_semua": request.user.has_perm(svc.IZIN_LIHAT_SEMUA),
            "dipotong": len(rows) >= MAKS_TAMPIL, "hari_tunda": svc.HARI_TUNDA,
            "form": PengaturanForm(instance=pengaturan) if kelola else None,
        })


@method_decorator(permission_required_or_denied(IZIN_LIHAT), name="dispatch")
class FollowUpAksiView(LoginRequiredMixin, View):
    def post(self, request, pk, aksi):
        row = get_object_or_404(svc.queryset_untuk(request.user), pk=pk)
        try:
            hari = int(request.POST.get("hari") or 7)
            svc.tandai(row, aksi, request.user, request.headers.get("HX-Prompt", ""), hari)
        except ValueError as exc:
            return _galat(str(exc))
        return _muat_ulang()


@method_decorator(permission_required_or_denied([IZIN_KELOLA]), name="dispatch")
class FollowUpPengaturanView(LoginRequiredMixin, View):
    def post(self, request):
        pengaturan = PengaturanFollowUp.ambil()
        form = PengaturanForm(request.POST, instance=pengaturan)
        if not form.is_valid():
            return _galat(" ".join(m for errs in form.errors.values() for m in errs))
        form.save()
        return _muat_ulang()


@method_decorator(permission_required_or_denied([IZIN_KELOLA]), name="dispatch")
class FollowUpSinkronView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            svc.sinkron_dorman()
        except bintang.BintangOrderError as exc:
            return _galat(f"Sinkron gagal: {exc}")
        return _muat_ulang()
