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


def normalisasi_nomor(nomor):
    """Nomor WA -> angka saja berawalan 62 ('0812-3456', '+62 812 3456', '62812..' menjadi sama).

    Nomor ERP tersimpan dalam format campuran; tanpa ini pelanggan yang sama dari dua jalur (pelanggan baru
    dan order kasir) menjadi dua Contact di CRM."""
    digit = "".join(ch for ch in str(nomor or "") if ch.isdigit())
    if digit.startswith("0"):
        digit = "62" + digit[1:]
    elif digit.startswith("8"):
        digit = "62" + digit
    return digit


def cari_kontak_per_nomor(nomor_wa):
    """Contact CRM untuk nomor ini: cocok persis dulu, lalu cocok setelah dinormalisasi."""
    from horilla_crm.contacts.models import Contact

    ada = Contact.objects.filter(bintang_contact_id=nomor_wa).first()
    if ada is not None:
        return ada
    baku = normalisasi_nomor(nomor_wa)
    if len(baku) < 8:
        return None
    for kandidat in Contact.objects.filter(bintang_contact_id__endswith=baku[-6:]):
        if normalisasi_nomor(kandidat.bintang_contact_id) == baku:
            return kandidat
    return None


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

    def _owner_untuk(self, request):
        """Pemilik data = penjual order bila punya akun CRM (tertaut hr_employee_id),
        sehingga staff hanya melihat penjualannya sendiri (peran staff di CRM hanya
        punya view_own_*). Selain itu pemilik bawaan = akun atasan (SPV), yang
        melihat semuanya lewat izin view_*. Order kasir saja yang mengirim
        `penjual_hr_employee_id`; penjualan POS lama tetap ke pemilik bawaan."""
        from horilla.contrib.core.models.user import HorillaUser

        try:
            hr_id = int(request.data.get('penjual_hr_employee_id'))
        except (TypeError, ValueError):
            hr_id = None
        if hr_id:
            penjual = HorillaUser.objects.filter(hr_employee_id=hr_id, is_active=True).first()
            if penjual is not None and penjual.company_id:
                return penjual
        return self._default_owner()

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        auth_error = self._cek_api_key(request)
        if auth_error:
            return auth_error

        from horilla_crm.contacts.models import Contact

        nomor_wa = str(request.data.get('nomor_wa') or '').strip()
        if not nomor_wa:
            return Response({'error': "Field 'nomor_wa' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        owner = self._owner_untuk(request)
        if owner is None:
            logger.error("Bintang bridge: user owner default ('%s') tidak ditemukan di CRM.", DEFAULT_OWNER_USERNAME)
            return Response({'error': 'Owner default CRM belum dikonfigurasi.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        first_name, last_name = _split_nama(request.data.get('nama'))
        email_masuk = str(request.data.get('email') or '').strip()
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
        contact = cari_kontak_per_nomor(nomor_wa)
        contact_created = contact is None
        if contact is None:
            contact = Contact(bintang_contact_id=nomor_wa, contact_owner=owner, company=owner.company)
            contact.contact_source = "other"
            contact.description = self._deskripsi_kontak(request.data)

        contact.first_name = first_name or contact.first_name or 'Pelanggan'
        contact.last_name = last_name
        # Email asli yang sudah tersimpan tidak ditimpa email pengganti (kiriman order sering tanpa email).
        if email_masuk:
            contact.email = email_masuk
        elif not contact.email or contact.email.endswith('@erp.local'):
            contact.email = f'{normalisasi_nomor(nomor_wa) or nomor_wa}@erp.local'
        if contact_created:
            contact.contact_number = nomor_wa
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
            opportunity_id, opportunity_created = self._upsert_opportunity(
                contact, owner, sale, nomor_wa=nomor_wa, email=str(request.data.get('email') or '').strip(),
            )

        return Response({
            'contact_id': contact.id,
            'contact_created': contact_created,
            'opportunity_id': opportunity_id,
            'opportunity_created': opportunity_created,
        }, status=status.HTTP_201_CREATED if contact_created else status.HTTP_200_OK)

    @staticmethod
    def _deskripsi_kontak(data):
        """Catatan asal-usul untuk Contact baru dari ERP (hanya diisi saat Contact dibuat)."""
        bagian = ["Pelanggan dari ERP"]
        if str(data.get("kode_pelanggan") or "").strip():
            bagian.append(f"kode {str(data['kode_pelanggan']).strip()}")
        if str(data.get("nama_perusahaan") or "").strip():
            bagian.append(f"perusahaan {str(data['nama_perusahaan']).strip()}")
        return ", ".join(bagian)

    def _upsert_opportunity(self, contact, owner, sale, nomor_wa="", email=""):
        from horilla_crm.opportunities import bintang_ringkasan
        from horilla_crm.opportunities.models import (
            Opportunity, OpportunityContactRole, OpportunityStage,
        )

        bintang_sale_id = str(sale.get('id'))[:40]
        # Order kasir mengirim `lunas`: False -> Opportunity Open, True -> Closed Won.
        # Tanpa field itu (penjualan POS) perilaku lama: langsung Closed Won.
        lunas = sale.get('lunas', True)
        existing = Opportunity.objects.filter(bintang_sale_id=bintang_sale_id).first()
        if existing:
            self._perbarui_opportunity(existing, sale, lunas, nomor_wa=nomor_wa)
            return existing.id, False

        stage_won = OpportunityStage.objects.filter(stage_type='won').order_by('order').first()
        if stage_won is None:
            logger.error("Bintang bridge: tidak ada OpportunityStage stage_type='won' di CRM -- opportunity dilewati.")
            return None, False
        stage_open = OpportunityStage.objects.filter(stage_type='open').order_by('order').first()
        stage = stage_won if (lunas or stage_open is None) else stage_open

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

        unit = str(sale.get('unit_bisnis') or '').strip() or 'ERP'
        menang = stage.stage_type == 'won'
        # Nama, deskripsi, jumlah barang, dan langkah berikutnya dari rincian order (lihat bintang_ringkasan).
        ringkasan = bintang_ringkasan.susun(sale, nomor, unit, nomor_wa, bool(lunas))
        opportunity = Opportunity.objects.create(
            name=ringkasan['name'],
            description=ringkasan['description'],
            next_step=ringkasan['next_step'],
            quantity=ringkasan.get('quantity'),
            email=email or None,
            amount=total,
            expected_revenue=total if menang else total * (stage.probability or 0) / 100,
            close_date=tanggal,
            stage=stage,
            probability=100 if menang else stage.probability,
            owner=owner,
            company=owner.company,
            opportunity_type='new_customer',
            lead_source='kasir',
            forecast_category='closed' if menang else 'pipeline',
            order_number=nomor[:8],
            bintang_sale_id=bintang_sale_id,
        )
        OpportunityContactRole.objects.create(contact=contact, opportunity=opportunity, is_primary=True)
        return opportunity.id, True

    def _perbarui_opportunity(self, opportunity, sale, lunas, nomor_wa=""):
        """Order kasir berubah: perbarui nilai selama masih Open; pindah ke Closed Won
        saat lunas. Nilai dan tahap Opportunity yang sudah Won/Lost tidak diubah lagi,
        tetapi teks rincian (nama, deskripsi, langkah berikutnya) tetap boleh diperbarui
        supaya Peluang lama bisa dijelaskan lewat sinkron ulang."""
        from horilla_crm.opportunities import bintang_ringkasan
        from horilla_crm.opportunities.bintang_order import tandai_menang

        masih_open = not opportunity.stage_id or opportunity.stage.stage_type == 'open'
        try:
            total = Decimal(str(sale.get('total') or 0))
        except InvalidOperation:
            return
        # Rincian (item, DP/sisa, status) ikut diperbarui hanya bila ERP mengirimnya (order kasir baru);
        # kiriman lama tanpa rincian tidak menimpa deskripsi yang sudah ada.
        if sale.get('items') is not None or sale.get('pelanggan'):
            nomor = str(sale.get('nomor') or opportunity.bintang_sale_id)
            unit = str(sale.get('unit_bisnis') or '').strip() or 'ERP'
            sudah_menang = bool(opportunity.stage_id) and opportunity.stage.stage_type == 'won'
            ringkasan = bintang_ringkasan.susun(sale, nomor, unit, nomor_wa, bool(lunas) or sudah_menang)
            opportunity.name = ringkasan['name']
            opportunity.description = ringkasan['description']
            opportunity.next_step = ringkasan['next_step']
            # Peluang lama dibuat sebelum sumber "Kasir / Toko" ada (bawaan "Lainnya"); isi saat dijelaskan ulang.
            if opportunity.lead_source in (None, '', 'other'):
                opportunity.lead_source = 'kasir'
            if ringkasan.get('quantity') is not None:
                opportunity.quantity = ringkasan['quantity']
            opportunity.save()
        if not masih_open:
            return
        if total and opportunity.amount != total:
            opportunity.amount = total
            opportunity.expected_revenue = total * (opportunity.probability or 0) / 100
            opportunity.save()
        if lunas is True:
            tandai_menang(opportunity.pk, total)


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
