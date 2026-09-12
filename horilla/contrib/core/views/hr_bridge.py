"""Jembatan HR (Horilla HR) -> CRM: endpoint server-ke-server dipanggil
OTOMATIS oleh sistem HR saat karyawan tim marketing baru dibuat atau
kandidat rekrutmen di-approve/convert jadi karyawan -- membuat akun CRM
yang tertaut ID-nya, supaya tidak ada identitas ganda antara HR & CRM.

Pola sama persis dengan jembatan HR->Bintang (bintang-advertising-backend/
api/views/hr_bridge.py): fail-closed kalau HR_BRIDGE_API_KEY belum
dikonfigurasi, API key sama yang dipakai bridge Bintang (satu kunci
dipercaya oleh HR ke kedua sistem tujuan).
"""
import logging
import os
import re
import secrets

from django.db import transaction
from django.utils.crypto import constant_time_compare
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from horilla.contrib.core.models.organization import Role
from horilla.contrib.core.models.user import HorillaUser

logger = logging.getLogger(__name__)

# Cuma departemen ini yang kerja di CRM (tim marketing) -- job position
# lain di-skip diam-diam (mereka pakai Bintang, bukan CRM).
DEPARTEMEN_DENGAN_AKUN_CRM = {'sales marketing & creative'}


def _map_job_position_ke_role(job_position: str):
    """Peta nama Job Position dari HR ke Role CRM yang sudah dibuat
    (lihat setup awal: 'SPV Sales Marketing & Creative' dengan sub-Role
    'Tim Sales Marketing & Creative'). None kalau tidak ada padanannya."""
    label = (job_position or '').strip()
    return Role.objects.filter(role_name__iexact=label).first()


def _buat_username_unik(nama_depan: str, nama_belakang: str) -> str:
    dasar = re.sub(r'[^a-z0-9.]', '', f"{nama_depan}.{nama_belakang}".strip('.').lower()) or 'karyawan'
    username = dasar
    counter = 2
    while HorillaUser.objects.filter(username=username).exists():
        username = f"{dasar}{counter}"
        counter += 1
    return username


class HRBridgeThrottle(AnonRateThrottle):
    scope = 'hr_bridge'
    rate = '30/min'


class HRBridgeCreateAccountView(APIView):
    """POST /api/bridge/hr-employee/

    Body: {
      "hr_employee_id": 42, "first_name": "Sinta", "last_name": "Marketing",
      "email": "sinta@contoh.com", "no_hp": "0812...",
      "job_position": "Tim Sales Marketing & Creative",
      "department": "Sales Marketing & Creative"
    }
    """
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    def _cek_api_key(self, request):
        expected = os.getenv("HR_BRIDGE_API_KEY")
        if not expected:
            logger.error("HR_BRIDGE_API_KEY belum dikonfigurasi. Endpoint HR bridge ditutup.")
            return Response({'error': 'HR bridge API belum dikonfigurasi di server.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        diberikan = request.headers.get('X-Api-Key', '') or ''
        if not diberikan or not constant_time_compare(diberikan, expected):
            logger.warning("HR bridge API: X-Api-Key tidak valid.")
            return Response({'error': 'Unauthorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return None

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        auth_error = self._cek_api_key(request)
        if auth_error:
            return auth_error

        hr_employee_id = request.data.get('hr_employee_id')
        if not hr_employee_id:
            return Response({'error': "Field 'hr_employee_id' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        department = str(request.data.get('department') or '').strip()
        if department.lower() not in DEPARTEMEN_DENGAN_AKUN_CRM:
            return Response({'skipped': True, 'reason': f"Departemen '{department}' tidak bekerja di CRM."}, status=status.HTTP_200_OK)

        first_name = str(request.data.get('first_name') or '').strip()
        last_name = str(request.data.get('last_name') or '').strip()
        email = str(request.data.get('email') or '').strip()
        no_hp = str(request.data.get('no_hp') or '').strip()
        job_position = str(request.data.get('job_position') or '').strip()
        role = _map_job_position_ke_role(job_position)

        existing = HorillaUser.objects.filter(hr_employee_id=hr_employee_id).first()
        if existing:
            existing.first_name = first_name or existing.first_name
            existing.last_name = last_name or existing.last_name
            existing.email = email or existing.email
            existing.contact_number = no_hp or existing.contact_number
            existing.role = role
            existing.save()
            return Response({
                'id': existing.id, 'username': existing.username,
                'role': role.role_name if role else None,
                'hr_employee_id': existing.hr_employee_id, 'created': False,
            }, status=status.HTTP_200_OK)

        username = _buat_username_unik(first_name, last_name)
        password_sementara = secrets.token_urlsafe(9)

        user = HorillaUser(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact_number=no_hp,
            role=role,
            hr_employee_id=hr_employee_id,
            country='ID',
        )
        user.set_password(password_sementara)
        user.save()

        return Response({
            'id': user.id, 'username': user.username,
            'role': role.role_name if role else None,
            'hr_employee_id': user.hr_employee_id, 'created': True,
            'temp_password': password_sementara,
        }, status=status.HTTP_201_CREATED)
