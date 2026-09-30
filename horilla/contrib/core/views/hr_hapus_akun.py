"""Karyawan dihapus di HR -> akun CRM-nya ikut dihapus (2026-09-30).

POST /api/bridge/hr-employee-hapus/  {"hr_employee_id": 42}   (X-Api-Key = HR_BRIDGE_API_KEY)

Aturan sama dengan jembatan Bintang: akun tanpa jejak dihapus bersih; akun yang
punya jejak (lead, aktivitas, dibuat-oleh di data lain, dst.) dinonaktifkan,
sandi dibuat tak bisa dipakai, dan data pribadi (email, nomor HP, foto)
dikosongkan supaya riwayat tidak rusak.
"""
import logging

from django.db import transaction
from django.db.models.deletion import Collector, ProtectedError, RestrictedError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla.contrib.core.models.user import HorillaUser

from .hr_bridge import HRBridgeThrottle
from .hr_organisasi import _cek_api_key

logger = logging.getLogger(__name__)

# Data milik pengguna sendiri, bukan riwayat bisnis: riwayat login dan pengaturan pintasan.
_BOLEH_IKUT_AWALAN = ('login_history.', 'keys.shortcutkey')


def _ada_isi(x):
    if hasattr(x, 'exists'):
        return x.exists()
    try:
        return any(_ada_isi(i) for i in x)
    except TypeError:
        return True


def _model_boleh(model):
    return model is HorillaUser or model._meta.auto_created or model._meta.label_lower.startswith(_BOLEH_IKUT_AWALAN)


def bisa_dihapus_bersih(user):
    if user.is_superuser:
        return False, 'akun superuser tidak dihapus otomatis'
    collector = Collector(using=user._state.db or 'default')
    try:
        collector.collect([user])
    except (ProtectedError, RestrictedError):
        return False, 'akun dipakai data lain yang dilindungi'
    for model in collector.data:
        if not _model_boleh(model):
            return False, f'ada data terkait ({model._meta.label})'
    for qs in collector.fast_deletes:
        if not _model_boleh(qs.model) and _ada_isi(qs):
            return False, f'ada data terkait ({qs.model._meta.label})'
    for grup in collector.field_updates.values():
        if _ada_isi(grup):
            return False, 'akun tercatat sebagai pembuat/pemilik di data lain'
    return True, ''


class HRBridgeHapusAkunView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    @transaction.atomic
    def post(self, request):
        auth_error = _cek_api_key(request)
        if auth_error:
            return auth_error
        hr_employee_id = request.data.get('hr_employee_id')
        if not hr_employee_id:
            return Response({'error': "Field 'hr_employee_id' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        user = HorillaUser.objects.select_for_update().filter(hr_employee_id=hr_employee_id).first()
        if user is None:
            return Response({'skipped': True, 'reason': 'Belum punya akun CRM.'})

        bersih, alasan = bisa_dihapus_bersih(user)
        if bersih:
            username = user.username
            user.delete()
            return Response({'mode': 'hapus', 'username': username})

        user.is_active = False
        user.set_unusable_password()
        user.email = ''
        user.contact_number = ''
        user.profile = None
        user.save()
        return Response({'mode': 'nonaktif', 'username': user.username, 'alasan': alasan})
