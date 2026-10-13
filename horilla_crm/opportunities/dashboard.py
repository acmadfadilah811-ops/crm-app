"""Dashboard utilities for opportunities module."""

# Standard library imports
import logging
from datetime import timedelta

# Third-party imports (Django)
from django.core.cache import cache
from django.utils import timezone
from django.utils.http import urlencode

from horilla.contrib.dashboard.utils import DefaultDashboardGenerator
from horilla.contrib.utils.methods import get_section_info_for_model

# First party imports (Horilla)
from horilla.db.models import Count
from horilla.utils.choices import TABLE_FALLBACK_FIELD_TYPES
from horilla.utils.translation import gettext_lazy as _

# Local imports
from horilla.urls import reverse
from horilla_crm.contacts.models import Contact

from .models import Opportunity

logger = logging.getLogger(__name__)


def create_opportunity_charts(self, queryset, model_info):
    """Create opportunity-specific charts"""
    try:
        if hasattr(queryset.model, "lead_source") or hasattr(queryset.model, "source"):
            source_field = (
                "lead_source" if hasattr(queryset.model, "lead_source") else "source"
            )
            source_data = (
                queryset.values(source_field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            if source_data.exists():
                labels = [item[source_field] or _("Unknown") for item in source_data]
                data = [item["count"] for item in source_data]

                section_info = get_section_info_for_model(queryset.model)
                urls = []
                for item in source_data:
                    value = item[source_field] or "Unknown"
                    query = urlencode(
                        {
                            "section": section_info["section"],
                            "apply_filter": "true",
                            "field": source_field,
                            "operator": "exact",
                            "value": value,
                        }
                    )
                    urls.append(f"{section_info['url']}?{query}")

                return {
                    "title": _("Opportunities by Lead Source"),
                    "type": "column",
                    "data": {
                        "labels": labels,
                        "urls": urls,
                        "data": data,
                        "labelField": _("Lead Source"),
                    },
                }

        stage_field = None
        if hasattr(queryset.model, "stage"):
            stage_field = "stage"
        elif hasattr(queryset.model, "status"):
            stage_field = "status"
        elif hasattr(queryset.model, "opportunity_stage"):
            stage_field = "opportunity_stage"

        if stage_field:
            stage_data = (
                queryset.values(stage_field)
                .annotate(count=Count("id"))
                .order_by("-count")
            )

            if stage_data.exists():
                labels = [item[stage_field] or _("Unknown") for item in stage_data]
                data = [item["count"] for item in stage_data]

                return {
                    "title": _("Opportunities by Stage"),
                    "type": "funnel",
                    "data": {"labels": labels, "data": data, "labelField": _("Stage")},
                }

        if hasattr(queryset.model, "is_won"):
            won_data = queryset.values("is_won").annotate(count=Count("id"))

            if won_data.exists():
                labels = []
                data = []
                for item in won_data:
                    status = _("Won") if item["is_won"] else _("In Progress/Lost")
                    labels.append(status)
                    data.append(item["count"])

                return {
                    "title": _("Opportunity Win Rate"),
                    "type": "pie",
                    "data": {
                        "labels": labels,
                        "data": data,
                        "labelField": _("Status"),
                    },
                }

        if hasattr(queryset.model, "amount") or hasattr(queryset.model, "value"):
            amount_field = "amount" if hasattr(queryset.model, "amount") else "value"

            opportunities = list(
                queryset.values("id", amount_field).exclude(
                    **{f"{amount_field}__isnull": True}
                )
            )
            if opportunities:
                ranges = [_("<10K"), _("10K-50K"), _("50K-100K"), _("100K+")]
                range_counts = [0, 0, 0, 0]

                for opp in opportunities:
                    amount = float(opp[amount_field] or 0)
                    if amount < 10000:
                        range_counts[0] += 1
                    elif amount < 50000:
                        range_counts[1] += 1
                    elif amount < 100000:
                        range_counts[2] += 1
                    else:
                        range_counts[3] += 1

                return {
                    "title": _("Opportunities by Value Range"),
                    "type": "column",
                    "data": {
                        "labels": ranges,
                        "data": range_counts,
                        "labelField": _("Value Range"),
                    },
                }

    except Exception as e:
        logger.warning("Error creating opportunity chart: %s", e)

    return None


def opportuntiy_table_fields(model_class):
    """Return list of {name, verbose_name} for opportuntiy table columns."""

    priority = ["name", "title", "account", "amount", "stage"]
    fields = []
    for name in priority:
        try:
            f = model_class._meta.get_field(name)
            fields.append(
                {
                    "name": name,
                    "verbose_name": f.verbose_name or name.replace("_", " ").title(),
                }
            )
        except Exception:
            continue
    if len(fields) < 4:
        for f in model_class._meta.fields:
            if len(fields) >= 4:
                break
            if (
                f.name not in [x["name"] for x in fields]
                and f.get_internal_type() in TABLE_FALLBACK_FIELD_TYPES
            ):
                fields.append(
                    {
                        "name": f.name,
                        "verbose_name": f.verbose_name
                        or f.name.replace("_", " ").title(),
                    }
                )
    return fields


def opportunity_table_func(generator, model_info):
    """Generate table context for won opportunities."""
    filter_kwargs = (
        {"stage__name": "Closed Won"} if hasattr(model_info["model"], "stage") else {}
    )

    return generator.build_table_context(
        model_info=model_info,
        title=_("Closed Won Opportunities"),
        filter_kwargs=filter_kwargs,
        no_found_img="assets/img/not-found-list.svg",
        no_record_msg=_("No closed won opportunities found."),
        view_id="opportunities_dashboard_list",
    )


DefaultDashboardGenerator.extra_models.append(
    {
        "model": Opportunity,
        "name": _("Opportunities"),
        "icon": "fa-handshake",
        "color": "purple",
        "include_kpi": True,
        "chart_func": create_opportunity_charts,
        "table_func": opportunity_table_func,
        "table_fields_func": opportuntiy_table_fields,
    }
)


# --- KPI omzet keseluruhan & follow up pelanggan (2026-10-13) -----------------

IZIN_LIHAT_SEMUA_OPP = "opportunities.view_opportunity"
MAKS_HARI_OMZET = 1099  # Bintang membatasi laporan 1100 hari.
CACHE_OMZET_DETIK = 300
CACHE_GAGAL_DETIK = 60


def _periode_omzet(generator):
    """Periode omzet mengikuti filter tanggal dasbor; 'semua' = 3 tahun terakhir."""
    hari_ini = timezone.localdate()
    rentang = generator.date_range
    if rentang == "custom":
        selesai = generator.date_to or hari_ini
        mulai = generator.date_from or (selesai - timedelta(days=29))
    elif rentang is None:
        selesai, mulai = hari_ini, hari_ini - timedelta(days=MAKS_HARI_OMZET)
    else:
        selesai, mulai = hari_ini, hari_ini - timedelta(days=int(rentang))
    if mulai > selesai:
        mulai = selesai
    if (selesai - mulai).days > MAKS_HARI_OMZET:
        mulai = selesai - timedelta(days=MAKS_HARI_OMZET)
    return mulai, selesai


def _omzet_bintang(mulai, selesai):
    """Ringkasan omzet dari Bintang, di-cache sebentar supaya dasbor tidak menunggu tiap dibuka."""
    from . import bintang_order as bintang

    kunci = f"crm:omzet:{mulai.isoformat()}:{selesai.isoformat()}"
    hasil = cache.get(kunci)
    if hasil is not None:
        return hasil or None
    try:
        hasil = bintang.laporan_penjualan(mulai, selesai, timeout=10)["ringkasan"]
    except (bintang.BintangOrderError, KeyError) as exc:
        logger.warning("Dasbor: omzet Bintang tidak bisa dimuat: %s", exc)
        cache.set(kunci, {}, CACHE_GAGAL_DETIK)
        return None
    cache.set(kunci, hasil, CACHE_OMZET_DETIK)
    return hasil


def omzet_kpi_func(generator, model_info):
    """Omzet keseluruhan semua kanal Bintang untuk atasan (pemegang izin lihat semua peluang).
    Definisi omzet sama dengan Laporan Sales dan Dashboard Eksekutif Bintang."""
    if not generator.user.has_perm(IZIN_LIHAT_SEMUA_OPP):
        return None
    from .views.bintang_order import _rp

    mulai, selesai = _periode_omzet(generator)
    section_info = get_section_info_for_model(Opportunity)
    url = f"{reverse('opportunities:laporan_sales')}?{urlencode({'mulai': mulai.isoformat(), 'selesai': selesai.isoformat()})}"
    ringkasan = _omzet_bintang(mulai, selesai)
    dasar = {"icon": "fa-sack-dollar", "type": "text", "url": url, "section": section_info.get("section")}
    if ringkasan is None:
        return [{**dasar, "title": _("Omzet Keseluruhan"), "value": _("Tidak bisa dimuat"), "color": "warning"}]
    return [
        {**dasar, "title": _("Omzet Keseluruhan"), "value": _rp(ringkasan["omzet"]), "color": "green"},
        {**dasar, "title": _("Omzet Sudah Dibayar"), "value": _rp(ringkasan["dibayar"]), "color": "teal"},
        {**dasar, "title": _("Omzet Belum Dibayar"), "value": _rp(ringkasan["belum_dibayar"]), "color": "orange"},
    ]


def follow_up_kpi_func(generator, model_info):
    """Jumlah pelanggan lama tidak order yang perlu di-follow up (atasan: semua, staff: miliknya)."""
    from .followup import jumlah_perlu_followup

    return {
        "title": _("Pelanggan Perlu Follow Up"),
        "value": jumlah_perlu_followup(generator.user),
        "type": "count",
        "icon": "fa-user-clock",
        "color": "orange",
        "url": reverse("opportunities:follow_up_pelanggan"),
        "section": get_section_info_for_model(Opportunity).get("section"),
    }


DefaultDashboardGenerator.extra_models.append(
    {
        "model": Opportunity,
        "name": _("Omzet ERP"),
        "icon": "fa-sack-dollar",
        "color": "green",
        "kpi_func": omzet_kpi_func,
    }
)

DefaultDashboardGenerator.extra_models.append(
    {
        "model": Contact,
        "name": _("Follow Up Pelanggan"),
        "icon": "fa-user-clock",
        "color": "orange",
        "kpi_func": follow_up_kpi_func,
    }
)
