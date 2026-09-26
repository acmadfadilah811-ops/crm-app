"""Tab "Riwayat Bintang" di detail Contact (2026-09-26, UAT SLS-04).

Menampilkan semua transaksi pelanggan di Bintang (order Antrean dari kanal
mana pun + penjualan POS) berdasarkan nomor HP Contact. Interaksi CRM tetap
di tab Activity/History bawaan.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View

from horilla.shortcuts import get_object_or_404, render
from horilla.utils.decorators import htmx_required, method_decorator
from horilla_crm.contacts.models import Contact
from horilla_crm.opportunities import bintang_order as bintang
from horilla_crm.opportunities.views.bintang_order import _rp


def boleh_lihat(user, contact):
    if user.has_perm("contacts.view_contact"):
        return True
    return user.has_perm("contacts.view_own_contact") and contact.contact_owner_id == user.id


@method_decorator(htmx_required, name="dispatch")
class ContactRiwayatBintangTabView(LoginRequiredMixin, View):
    template_name = "contacts/riwayat_bintang_tab.html"

    def get(self, request, pk):
        contact = get_object_or_404(Contact, pk=pk)
        if not boleh_lihat(request.user, contact):
            return HttpResponse(
                '<div class="p-4 text-sm text-red-600">Anda tidak berhak melihat riwayat pelanggan ini.</div>',
                status=403,
            )
        nomor = (contact.contact_number or contact.bintang_contact_id or "").strip()
        data, galat = None, None
        if not nomor:
            galat = "Contact ini belum punya nomor HP, jadi riwayat Bintang tidak bisa dicari."
        else:
            try:
                data = bintang.riwayat_pelanggan(nomor)
            except bintang.BintangOrderError as exc:
                galat = str(exc)
        if data:
            data["total_rp"], data["sisa_rp"] = _rp(data.get("total_belanja_lunas")), _rp(data.get("sisa_tagihan"))
            for e in data.get("riwayat", []):
                e["total_rp"], e["sisa_rp"] = _rp(e.get("total")), _rp(e.get("sisa"))
        return render(request, self.template_name, {"contact": contact, "data": data, "galat": galat, "nomor": nomor})
