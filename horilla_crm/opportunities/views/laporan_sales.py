"""Laporan Sales & Marketing (2026-09-26, UAT SLS-01/02).

Satu halaman untuk SPV/Manager (izin umum view_opportunity) dengan periode bebas:
- Penjualan Bintang per kanal & per bulan + pertumbuhan pelanggan (dari Bintang;
  definisi omzet sama dengan Dashboard Eksekutif sehingga bisa dicek silang).
- Kinerja per Sales dari order yang dibuat lewat CRM (dari Bintang).
- Lead, Opportunity, dan Campaign (data CRM sendiri).
"""

import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Sum
from django.views import View

from horilla.contrib.core.models.user import HorillaUser
from horilla.shortcuts import render
from horilla.utils.decorators import method_decorator, permission_required_or_denied
from horilla_crm.campaigns.models import Campaign
from horilla_crm.leads.models import Lead
from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities.models import Opportunity
from horilla_crm.opportunities.views.bintang_order import _rp


def _periode(request):
    hari_ini = datetime.date.today()
    try:
        mulai = datetime.date.fromisoformat(request.GET.get("mulai", ""))
    except ValueError:
        mulai = hari_ini.replace(day=1)
    try:
        selesai = datetime.date.fromisoformat(request.GET.get("selesai", ""))
    except ValueError:
        selesai = hari_ini
    return mulai, selesai


def _persen(a, b):
    return round(a * 100 / b, 1) if b else 0


def _laporan_crm(mulai, selesai):
    leads = Lead.objects.filter(created_at__date__gte=mulai, created_at__date__lte=selesai)
    sumber = dict(Lead._meta.get_field("lead_source").choices)
    per_sumber = [
        {"sumber": sumber.get(r["lead_source"], r["lead_source"] or "-"), "jumlah": r["n"], "konversi": r["k"],
         "persen": _persen(r["k"], r["n"])}
        for r in leads.values("lead_source").annotate(n=Count("id"), k=Count("id", filter=Q(is_convert=True))).order_by("-n")
    ]
    tutup = Opportunity.objects.filter(close_date__gte=mulai, close_date__lte=selesai)
    menang = tutup.filter(stage__stage_type="won")
    jumlah_lead = leads.count()
    jumlah_konversi = leads.filter(is_convert=True).count()
    campaigns = Campaign.objects.filter(
        Q(start_date__isnull=True) | Q(start_date__lte=selesai),
        Q(end_date__isnull=True) | Q(end_date__gte=mulai),
    ).order_by("-start_date")[:50]
    return {
        "lead_baru": jumlah_lead,
        "lead_konversi": jumlah_konversi,
        "lead_persen": _persen(jumlah_konversi, jumlah_lead),
        "lead_per_sumber": per_sumber,
        "opp_baru": Opportunity.objects.filter(created_at__date__gte=mulai, created_at__date__lte=selesai).count(),
        "opp_menang": menang.count(),
        "opp_kalah": tutup.filter(stage__stage_type="lost").count(),
        "opp_menang_rp": _rp(menang.aggregate(v=Sum("amount"))["v"] or 0),
        "campaigns": [
            {
                "nama": c.campaign_name, "status": c.get_status_display(), "jenis": c.get_campaign_type_display(),
                "mulai": c.start_date, "selesai": c.end_date, "lead": c.leads_in_campaign or 0,
                "konversi": c.converted_leads_in_campaign or 0, "respon": c.responses_in_campaign or 0,
                "menang": c.won_opportunities_in_campaign or 0, "menang_rp": _rp(c.value_won_opportunities or 0),
                "biaya_rp": _rp(c.actual_cost or 0),
            }
            for c in campaigns
        ],
    }


@method_decorator(permission_required_or_denied(["opportunities.view_opportunity"]), name="dispatch")
class LaporanSalesView(LoginRequiredMixin, View):
    template_name = "opportunities/laporan_sales.html"

    def get(self, request):
        mulai, selesai = _periode(request)
        konteks = {"mulai": mulai, "selesai": selesai, "galat": None, "bintang": None, "per_sales": []}
        if mulai > selesai:
            konteks["galat"] = "Tanggal mulai harus sebelum tanggal selesai."
        else:
            try:
                data = bintang.laporan_penjualan(mulai, selesai)
                r = data["ringkasan"]
                for k in ("omzet", "dibayar", "belum_dibayar"):
                    r[f"{k}_rp"] = _rp(r[k])
                for baris in data["per_kanal"] + data["per_bulan"]:
                    baris["omzet_rp"] = _rp(baris["omzet"])
                for baris in data["per_kanal"]:
                    baris["porsi"] = _persen(baris["omzet"], r["omzet"])
                konteks["bintang"] = data
                rekap = bintang.rekap_sales(mulai, selesai, [])
                nama = {u.pk: u.get_full_name() or u.get_username()
                        for u in HorillaUser.objects.filter(pk__in=rekap.keys())}
                konteks["per_sales"] = sorted(
                    ({**v, "nama": nama.get(k, f"Akun #{k}"), "nilai_rp": _rp(v["nilai_lunas"]),
                      "belum_rp": _rp(v["nilai_belum_lunas"])} for k, v in rekap.items()),
                    key=lambda x: -x["nilai_lunas"],
                )
            except bintang.BintangOrderError as exc:
                konteks["galat"] = str(exc)
            konteks["crm"] = _laporan_crm(mulai, selesai)
        return render(request, self.template_name, konteks)
