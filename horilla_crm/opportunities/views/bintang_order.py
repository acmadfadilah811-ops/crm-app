"""Tab "Order Bintang" di detail Opportunity (2026-09-26).

Sales membuat order dari Opportunity -> order draft di Antrean kasir Bintang,
lalu memantau statusnya di tab yang sama (UAT MKT-02, MKT-03, MKT-04, MKT-06).
Aturan bisnis ada di Bintang (api/services/crm_order.py); CRM hanya meneruskan.
"""

import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.views import View

from horilla.shortcuts import get_object_or_404, render
from horilla.utils.decorators import htmx_required, method_decorator
from horilla.web import ScriptResponse
from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities.models import Opportunity

MAKS_BARIS = 50


def _boleh(user, opportunity, aksi):
    """aksi: 'view' atau 'change'. Izin umum, atau izin 'own' untuk pemilik Opportunity."""
    if user.has_perm(f"opportunities.{aksi}_opportunity"):
        return True
    return user.has_perm(f"opportunities.{aksi}_own_opportunity") and opportunity.owner_id == user.id


def _rp(x):
    try:
        return "Rp " + f"{int(x):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def _kontak_utama(opportunity):
    role = (
        opportunity.contact_roles.select_related("contact").order_by("-is_primary", "id").first()
        if hasattr(opportunity, "contact_roles") else None
    )
    return role.contact if role else None


def _tolak():
    return HttpResponse(
        '<div class="p-4 text-sm text-red-600">Anda tidak berhak mengakses order untuk prospek ini.</div>',
        status=403,
    )


@method_decorator(htmx_required, name="dispatch")
class OpportunityOrderBintangTabView(LoginRequiredMixin, View):
    """Daftar order Bintang milik Opportunity ini + tombol Buat Order."""

    template_name = "opportunities/order_bintang_tab.html"

    def get(self, request, pk):
        opp = get_object_or_404(Opportunity, pk=pk)
        if not _boleh(request.user, opp, "view"):
            return _tolak()
        orders, galat = [], None
        try:
            orders = bintang.order_per_opportunity(opp.pk)
            for o in orders:
                o["total_rp"], o["sisa_rp"] = _rp(o.get("total_harga")), _rp(o.get("sisa_tagihan"))
        except bintang.BintangOrderError as exc:
            galat = str(exc)
        # Cadangan bila kiriman otomatis Bintang saat lunas gagal sampai.
        lunas = [o for o in orders if o.get("lunas")]
        if lunas and not (opp.stage_id and opp.stage.stage_type == "won"):
            if bintang.tandai_menang(opp.pk, sum(int(o.get("total_harga") or 0) for o in lunas)):
                opp.refresh_from_db()
        return render(request, self.template_name, {
            "opportunity": opp, "orders": orders, "galat": galat,
            "bisa_buat": _boleh(request.user, opp, "change"),
        })


@method_decorator(htmx_required, name="dispatch")
class OpportunityOrderBintangFormView(LoginRequiredMixin, View):
    """GET: form order (modal). POST: kirim ke Bintang."""

    template_name = "opportunities/order_bintang_form.html"

    def _konteks(self, opp, data=None, galat=None):
        kontak = _kontak_utama(opp)
        data = data or {
            "nama": str(kontak) if kontak else (opp.account.name if opp.account_id else ""),
            "nomor_hp": getattr(kontak, "contact_number", "") or "",
            "email": getattr(kontak, "email", "") or "",
            "catatan": "",
            "kunci": f"crm-opp{opp.pk}-{uuid.uuid4().hex[:16]}",
            "baris": [],
        }
        return {"opportunity": opp, "data": data, "galat": galat, "kontak_id": getattr(kontak, "pk", None)}

    def get(self, request, pk):
        opp = get_object_or_404(Opportunity, pk=pk)
        if not _boleh(request.user, opp, "change"):
            return _tolak()
        return render(request, self.template_name, self._konteks(opp))

    def post(self, request, pk):
        opp = get_object_or_404(Opportunity, pk=pk)
        if not _boleh(request.user, opp, "change"):
            return _tolak()
        p = request.POST
        baris = []
        for pid, nama, qty, ket in zip(p.getlist("product_id"), p.getlist("product_nama"),
                                       p.getlist("qty"), p.getlist("keterangan")):
            if pid:
                baris.append({"product_id": pid, "nama": nama, "qty": qty, "keterangan": ket})
        data = {
            "nama": p.get("nama", "").strip(), "nomor_hp": p.get("nomor_hp", "").strip(),
            "email": p.get("email", "").strip(), "catatan": p.get("catatan", "").strip(),
            "kunci": p.get("kunci", ""), "baris": baris[:MAKS_BARIS],
        }
        kontak = _kontak_utama(opp)
        payload = {
            "kunci": data["kunci"],
            "crm_user_id": request.user.pk,
            "crm_username": request.user.get_username(),
            "sales_nama": request.user.get_full_name() or request.user.get_username(),
            "crm_opportunity_id": opp.pk,
            "crm_contact_id": getattr(kontak, "pk", None),
            "pelanggan": {"nama": data["nama"], "nomor_hp": data["nomor_hp"], "email": data["email"]},
            "items": [{"product_id": b["product_id"], "qty": b["qty"], "keterangan": b["keterangan"]} for b in baris],
            "catatan": data["catatan"],
        }
        try:
            bintang.buat_order(payload)
        except bintang.BintangOrderError as exc:
            return render(request, self.template_name, self._konteks(opp, data, str(exc)))
        return ScriptResponse(extra="htmx.trigger('#tab-order-bintang','click');", close=True)


class ProdukBintangCariView(LoginRequiredMixin, View):
    """GET ?q= -> JSON produk katalog Bintang (untuk form order)."""

    def get(self, request):
        if not (request.user.has_perm("opportunities.change_opportunity")
                or request.user.has_perm("opportunities.change_own_opportunity")):
            return JsonResponse({"error": "Tidak berhak."}, status=403)
        q = (request.GET.get("q") or "").strip()
        if len(q) < 2:
            return JsonResponse({"hasil": []})
        try:
            return JsonResponse({"hasil": bintang.cari_produk(q)})
        except bintang.BintangOrderError as exc:
            return JsonResponse({"error": str(exc)}, status=502)
