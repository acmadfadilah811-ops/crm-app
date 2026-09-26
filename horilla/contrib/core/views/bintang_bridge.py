"""Jembatan Bintang -> CRM: endpoint server-ke-server dipanggil OTOMATIS
oleh Bintang setiap kali POS Sale berstatus 'paid' -- membuat/update
Contact CRM (dedup by nomor WA) dan Opportunity "Closed Won" (dedup by
ID penjualan Bintang), supaya CRM punya data pelanggan & histori
penjualan real dari Bintang tanpa entri manual.

Pola sama persis dengan jembatan HR->CRM di package ini (hr_bridge.py):
fail-closed kalau BINTANG_BRIDGE_API_KEY belum dikonfigurasi, X-Api-Key
header, constant_time_compare.
"""
import datetime
import logging
import os
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

# Owner default untuk Contact/Opportunity hasil sync -- tim yang memang
# menangani sales/marketing di CRM ini (lihat hr_bridge.py:
# DEPARTEMEN_DENGAN_AKUN_CRM). Instruksi eksplisit user: pakai akun SPV,
# bukan admin/superuser, supaya relevan secara peran.
DEFAULT_OWNER_USERNAME = 'spv.salesmarketingcreative'


def _split_nama(nama: str):
    """Contact CRM wajib first_name+last_name terpisah; Bintang cuma
    punya satu field 'nama'. Kata pertama jadi first_name, sisanya last_name
    -- kalau cuma satu kata, last_name diisi string kosong (field ini wajib
    diisi non-null di model tapi boleh blank)."""
    bagian = (nama or '').strip().split(None, 1)
    if not bagian:
        return 'Pelanggan', ''
    if len(bagian) == 1:
        return bagian[0], ''
    return bagian[0], bagian[1]


class BintangBridgeThrottle(AnonRateThrottle):
    scope = 'bintang_bridge'
    rate = '60/min'


class BintangBridgeSaleView(APIView):
    """POST /api/bridge/bintang-sale/

    Body: {
      "nomor_wa": "6281234567890", "nama": "Budi Santoso",
      "email": "budi@contoh.com", "alamat": "...", "kota": "...",
      "provinsi": "...", "negara": "...", "kode_pos": "...",
      "nama_perusahaan": "...",
      "sale": {
        "id": "possale:123", "nomor": "POS-0001",
        "total": 500000, "tanggal": "2026-09-17"
      }
    }

    "sale" opsional -- kalau tidak ada cuma Contact yang di-upsert (tanpa
    bikin Opportunity). Response: {"contact_id":.., "contact_created":..,
    "opportunity_id":.. atau null, "opportunity_created":..}.
    """

    permission_classes = [AllowAny]
    throttle_classes = [BintangBridgeThrottle]

    def _cek_api_key(self, request):
        expected = os.getenv('BINTANG_BRIDGE_API_KEY')
        if not expected:
            logger.error('BINTANG_BRIDGE_API_KEY belum dikonfigurasi. Endpoint Bintang bridge ditutup.')
            return Response({'error': 'Bintang bridge API belum dikonfigurasi di server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        diberikan = request.headers.get('X-Api-Key', '') or ''
        if not diberikan or not constant_time_compare(diberikan, expected):
            logger.warning('Bintang bridge API: X-Api-Key tidak valid.')
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return None

    def _default_owner(self):
        from horilla.contrib.core.models.user import HorillaUser
        return HorillaUser.objects.filter(username=DEFAULT_OWNER_USERNAME).first()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        auth_error = self._cek_api_key(request)
        if auth_error:
            return auth_error

        from horilla_crm.contacts.models import Contact

        nomor_wa = str(request.data.get('nomor_wa') or '').strip()
        if not nomor_wa:
            return Response({'error': "Field 'nomor_wa' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        owner = self._default_owner()
        if owner is None:
            logger.error("Bintang bridge: user owner default ('%s') tidak ditemukan di CRM.", DEFAULT_OWNER_USERNAME)
            return Response({'error': 'Owner default CRM belum dikonfigurasi.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        first_name, last_name = _split_nama(request.data.get('nama'))
        email = str(request.data.get('email') or '').strip() or f'{nomor_wa}@bintang.local'
        contact_number = nomor_wa
        alamat_kota = str(request.data.get('kota') or '').strip()
        alamat_provinsi = str(request.data.get('provinsi') or '').strip()
        # address_country adalah CountryField (kode ISO 2 huruf) -- Customer
        # Bintang free-text (mis. "Indonesia"), jadi apa pun selain kode
        # 2-huruf yang valid, default ke 'ID' (bisnis Indonesia-only).
        alamat_negara_raw = str(request.data.get('negara') or '').strip().upper()
        alamat_negara = alamat_negara_raw if len(alamat_negara_raw) == 2 else 'ID'
        alamat_zip = str(request.data.get('kode_pos') or '').strip()

        # CompanyFilteredManager (objects) hanya nampilin baris yang
        # company-nya cocok sama active_company sesi browser -- tanpa ini,
        # Contact/Opportunity hasil sync JADI ADA di database tapi TIDAK
        # KELIHATAN sama sekali di UI CRM (ditemukan lewat audit data dummy).
        contact = Contact.objects.filter(bintang_contact_id=nomor_wa).first()
        contact_created = contact is None
        if contact is None:
            contact = Contact(bintang_contact_id=nomor_wa, contact_owner=owner, company=owner.company)

        contact.first_name = first_name or contact.first_name or 'Pelanggan'
        contact.last_name = last_name
        contact.email = email
        contact.contact_number = contact_number
        if alamat_kota:
            contact.address_city = alamat_kota
        if alamat_provinsi:
            contact.address_state = alamat_provinsi
        if alamat_zip:
            contact.address_zip = alamat_zip
        contact.address_country = alamat_negara
        contact.save()

        sale = request.data.get('sale')
        opportunity_id = None
        opportunity_created = False
        if isinstance(sale, dict) and sale.get('id'):
            opportunity_id, opportunity_created = self._upsert_opportunity(contact, owner, sale)

        return Response({
            'contact_id': contact.id,
            'contact_created': contact_created,
            'opportunity_id': opportunity_id,
            'opportunity_created': opportunity_created,
        }, status=status.HTTP_201_CREATED if contact_created else status.HTTP_200_OK)

    def _upsert_opportunity(self, contact, owner, sale):
        from horilla_crm.opportunities.models import (
            Opportunity, OpportunityContactRole, OpportunityStage,
        )

        bintang_sale_id = str(sale.get('id'))
        existing = Opportunity.objects.filter(bintang_sale_id=bintang_sale_id).first()
        if existing:
            return existing.id, False

        stage_won = OpportunityStage.objects.filter(stage_type='won').order_by('order').first()
        if stage_won is None:
            logger.error("Bintang bridge: tidak ada OpportunityStage stage_type='won' di CRM -- opportunity dilewati.")
            return None, False

        nomor = str(sale.get('nomor') or bintang_sale_id)
        # Opportunity.save() menghitung expected_revenue = amount *
        # (probability / 100) -- probability adalah Decimal, jadi amount
        # HARUS Decimal juga (float * Decimal -> TypeError). Payload JSON
        # dari Bintang bisa berupa float (mis. 7500.0).
        try:
            total = Decimal(str(sale.get('total') or 0))
        except InvalidOperation:
            total = Decimal('0')
        tanggal_raw = sale.get('tanggal')
        try:
            tanggal = datetime.date.fromisoformat(tanggal_raw) if tanggal_raw else datetime.date.today()
        except ValueError:
            tanggal = datetime.date.today()

        opportunity = Opportunity.objects.create(
            name=f'Penjualan Bintang {nomor}',
            amount=total,
            expected_revenue=total,
            close_date=tanggal,
            stage=stage_won,
            probability=100,
            owner=owner,
            company=owner.company,
            opportunity_type='new_customer',
            lead_source='other',
            forecast_category='closed',
            order_number=nomor[:8],
            bintang_sale_id=bintang_sale_id,
        )
        OpportunityContactRole.objects.create(contact=contact, opportunity=opportunity, is_primary=True)
        return opportunity.id, True


class BintangBridgeOrderLunasView(BintangBridgeSaleView):
    """POST /api/bridge/bintang-order-lunas/

    Dipanggil Bintang saat order yang dibuat Sales dari CRM menjadi lunas.
    Body: {"crm_opportunity_id": 12, "order_id": "ORD-...", "total_harga": 125000}
    Opportunity tersebut dipindah ke stage won (Closed Won). Idempoten.
    Response: {"opportunity_id":.., "diubah": true/false}.
    """

    def post(self, request, *args, **kwargs):
        auth_error = self._cek_api_key(request)
        if auth_error:
            return auth_error
        from horilla_crm.opportunities.bintang_order import tandai_menang

        try:
            opp_id = int(request.data.get('crm_opportunity_id'))
        except (TypeError, ValueError):
            return Response({'error': "Field 'crm_opportunity_id' wajib angka."}, status=status.HTTP_400_BAD_REQUEST)
        hasil = tandai_menang(opp_id, request.data.get('total_harga'))
        if hasil is None:
            return Response({'error': 'Opportunity tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)
        logger.info('Bintang order %s lunas -> Opportunity %s won (diubah=%s).', request.data.get('order_id'), opp_id, hasil)
        return Response({'opportunity_id': opp_id, 'diubah': hasil})
