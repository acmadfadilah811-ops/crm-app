"""Target Sales (2026-09-26, UAT SLS-05/06).

SPV/Manager (izin umum change_opportunity) mengatur target per Sales dengan
periode bebas: target nilai (Rp) dan/atau target jumlah order. Sales melihat
target miliknya sendiri. Realisasi diambil dari Bintang per periode.
"""

import datetime

from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from horilla.contrib.core.models.user import HorillaUser
from horilla.shortcuts import get_object_or_404, render
from horilla.utils.decorators import htmx_required, method_decorator, permission_required_or_denied
from horilla.web import ScriptResponse
from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities.target_models import TargetSales
from horilla_crm.opportunities.views.bintang_order import _rp

MAKS_TAMPIL = 50
IZIN_KELOLA = "opportunities.change_opportunity"
KELAS_INPUT = "w-full border border-dark-50 rounded-md px-3 py-2 text-sm"


def _persen(capai, target):
    if not target:
        return None
    return round(float(capai) * 100 / float(target), 1)


class TargetSalesForm(forms.ModelForm):
    class Meta:
        model = TargetSales
        fields = ["sales", "nama_periode", "tanggal_mulai", "tanggal_selesai",
                  "target_nilai", "target_jumlah_order", "catatan"]
        labels = {
            "sales": "Sales", "nama_periode": "Nama periode", "tanggal_mulai": "Tanggal mulai",
            "tanggal_selesai": "Tanggal selesai", "target_nilai": "Target nilai (Rp, dari order lunas)",
            "target_jumlah_order": "Target jumlah order", "catatan": "Catatan",
        }
        widgets = {
            "tanggal_mulai": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "tanggal_selesai": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sales"].queryset = HorillaUser.objects.filter(
            is_active=True, role__isnull=False,
        ).order_by("first_name", "last_name")
        self.fields["sales"].label_from_instance = lambda u: u.get_full_name() or u.get_username()
        for f in self.fields.values():
            f.widget.attrs.setdefault("class", KELAS_INPUT)


def _realisasi(targets):
    """Tempel realisasi dari Bintang ke tiap target. Return pesan galat atau None."""
    per_periode = {}
    for t in targets:
        per_periode.setdefault((t.tanggal_mulai, t.tanggal_selesai), set()).add(t.sales_id)
    galat, data = None, {}
    for (mulai, selesai), ids in per_periode.items():
        try:
            data[(mulai, selesai)] = bintang.rekap_sales(mulai, selesai, sorted(ids))
        except bintang.BintangOrderError as exc:
            galat = str(exc)
            break
    kosong = {"jumlah_order": 0, "jumlah_lunas": 0, "nilai_lunas": 0, "nilai_belum_lunas": 0}
    hari_ini = datetime.date.today()
    for t in targets:
        r = kosong if galat else data.get((t.tanggal_mulai, t.tanggal_selesai), {}).get(t.sales_id, kosong)
        t.real = r
        t.nilai_rp, t.target_rp = _rp(r["nilai_lunas"]), _rp(t.target_nilai)
        t.belum_lunas_rp = _rp(r["nilai_belum_lunas"])
        t.persen_nilai = _persen(r["nilai_lunas"], t.target_nilai)
        t.persen_jumlah = _persen(r["jumlah_order"], t.target_jumlah_order)
        t.lebar_nilai = min(100, t.persen_nilai or 0)
        t.lebar_jumlah = min(100, t.persen_jumlah or 0)
        if hari_ini < t.tanggal_mulai:
            t.keadaan = "Belum mulai"
        elif hari_ini > t.tanggal_selesai:
            t.keadaan = "Selesai"
        else:
            t.keadaan = f"Berjalan, sisa {(t.tanggal_selesai - hari_ini).days} hari"
    return galat


@method_decorator(
    permission_required_or_denied(["opportunities.view_opportunity", "opportunities.view_own_opportunity"]),
    name="dispatch",
)
class TargetSalesView(LoginRequiredMixin, View):
    template_name = "opportunities/target_sales.html"

    def get(self, request):
        kelola = request.user.has_perm(IZIN_KELOLA)
        qs = TargetSales.objects.select_related("sales")
        if not kelola:
            qs = qs.filter(sales=request.user)
        sales_id = request.GET.get("sales", "")
        if kelola and sales_id.isdigit():
            qs = qs.filter(sales_id=int(sales_id))
        semua_periode = request.GET.get("periode") == "semua"
        if not semua_periode:
            qs = qs.filter(tanggal_selesai__gte=datetime.date.today())
        targets = list(qs[:MAKS_TAMPIL])
        galat = _realisasi(targets) if targets else None
        return render(request, self.template_name, {
            "targets": targets, "galat": galat, "kelola": kelola,
            "semua_periode": semua_periode, "sales_id": sales_id,
            "daftar_sales": TargetSalesForm().fields["sales"].queryset if kelola else [],
        })


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied([IZIN_KELOLA]), name="dispatch")
class TargetSalesFormView(LoginRequiredMixin, View):
    template_name = "opportunities/target_sales_form.html"

    def get(self, request, pk=None):
        obj = get_object_or_404(TargetSales, pk=pk) if pk else None
        return render(request, self.template_name, {"form": TargetSalesForm(instance=obj), "obj": obj})

    def post(self, request, pk=None):
        obj = get_object_or_404(TargetSales, pk=pk) if pk else None
        form = TargetSalesForm(request.POST, instance=obj)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form, "obj": obj})
        target = form.save(commit=False)
        if obj is None:
            target.dibuat_oleh = request.user
        target.save()
        return ScriptResponse(close=True, extra="window.location.reload();")


@method_decorator(htmx_required, name="dispatch")
@method_decorator(permission_required_or_denied([IZIN_KELOLA]), name="dispatch")
class TargetSalesHapusView(LoginRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(TargetSales, pk=pk).delete()
        return HttpResponse("<script>window.location.reload();</script>")
