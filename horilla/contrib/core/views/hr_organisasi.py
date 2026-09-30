"""Jembatan HR -> CRM untuk struktur organisasi (2026-09-30).

POST /api/bridge/hr-organisasi/   (X-Api-Key = HR_BRIDGE_API_KEY, sama dgn jembatan akun)
  {"jenis": "departemen", "nama": "Sales Marketing & Creative", "nama_lama": null}
  {"jenis": "jabatan", "nama": "Tim Sales Marketing & Creative", "nama_lama": null,
   "departemen": "Sales Marketing & Creative"}

- Departemen HR -> Department CRM
- Jabatan HR    -> Role CRM (parent = "SPV <departemen>" bila ada, kecuali jabatan SPV itu sendiri)
Hanya departemen tim marketing yang bekerja di CRM; departemen lain dilewati.
Tidak pernah menghapus. CRM tidak menyimpan ID HR, jadi ganti nama dicocokkan lewat
`nama_lama` yang dikirim HR.
"""
import logging
import os

from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla.contrib.core.models.base import Company
from horilla.contrib.core.models.organization import Department, Role

from .hr_bridge import DEPARTEMEN_DENGAN_AKUN_CRM, HRBridgeThrottle

logger = logging.getLogger(__name__)


def _cek_api_key(request):
    expected = os.getenv("HR_BRIDGE_API_KEY")
    if not expected:
        logger.error("HR_BRIDGE_API_KEY belum dikonfigurasi. Endpoint HR bridge ditutup.")
        return Response({'error': 'HR bridge API belum dikonfigurasi di server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    diberikan = request.headers.get('X-Api-Key', '') or ''
    if not diberikan or not constant_time_compare(diberikan, expected):
        logger.warning("HR bridge API: X-Api-Key tidak valid.")
        return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
    return None


def _sinkron_department(nama, nama_lama):
    obj = None
    for kandidat in filter(None, [nama_lama, nama]):
        obj = Department.objects.filter(department_name__iexact=kandidat).first()
        if obj:
            break
    if obj is None:
        return Department.objects.create(department_name=nama, company=Company.objects.first()), True
    if obj.department_name != nama:
        obj.department_name = nama
        obj.save()
    return obj, False


def _sinkron_role(nama, nama_lama, departemen):
    obj = None
    for kandidat in filter(None, [nama_lama, nama]):
        obj = Role.objects.filter(role_name__iexact=kandidat).first()
        if obj:
            break
    induk = None
    if not nama.lower().startswith('spv'):
        induk = Role.objects.filter(role_name__iexact=f'SPV {departemen}').first()
    if obj is None:
        return Role.objects.create(role_name=nama, parent_role=induk, company=Company.objects.first()), True
    obj.role_name = nama
    if induk and obj.parent_role_id is None and induk.pk != obj.pk:
        obj.parent_role = induk
    obj.save()
    return obj, False


class HROrganisasiView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    @transaction.atomic
    def post(self, request):
        auth_error = _cek_api_key(request)
        if auth_error:
            return auth_error

        jenis = str(request.data.get('jenis') or '')
        nama = str(request.data.get('nama') or '').strip()
        nama_lama = str(request.data.get('nama_lama') or '').strip() or None
        departemen = str(request.data.get('departemen') or (nama if jenis == 'departemen' else '')).strip()
        if not nama:
            return Response({'error': "Field 'nama' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        if departemen.lower() not in DEPARTEMEN_DENGAN_AKUN_CRM:
            return Response({'skipped': True, 'reason': f"Departemen '{departemen}' tidak bekerja di CRM."})

        if jenis == 'departemen':
            obj, dibuat = _sinkron_department(nama, nama_lama)
            return Response({'id': obj.id, 'nama': obj.department_name, 'created': dibuat})
        if jenis == 'jabatan':
            obj, dibuat = _sinkron_role(nama, nama_lama, departemen)
            return Response({'id': obj.id, 'nama': obj.role_name, 'created': dibuat})
        return Response({'error': "Field 'jenis' harus 'departemen' atau 'jabatan'."}, status=status.HTTP_400_BAD_REQUEST)
