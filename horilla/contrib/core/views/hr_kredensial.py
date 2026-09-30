"""Penyatuan kredensial akun LAMA CRM dengan HR (2026-09-30).

POST /api/bridge/hr-employee-kredensial/  (X-Api-Key = HR_BRIDGE_API_KEY)
  {"hr_employee_id": 42, "hanya_lihat": true}   -> username sekarang
  {"hr_employee_id": 42, "username": "budi.santoso", "password": "..."}
409 bila username dipakai akun lain; akun nonaktif dilewati.
"""
import re

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla.contrib.core.models.user import HorillaUser

from .hr_bridge import HRBridgeThrottle
from .hr_organisasi import _cek_api_key

POLA_USERNAME = re.compile(r"[a-z0-9.]{3,50}")


class HRBridgeKredensialView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    @transaction.atomic
    def post(self, request):
        auth_error = _cek_api_key(request)
        if auth_error:
            return auth_error
        hr_id = request.data.get("hr_employee_id")
        if not hr_id:
            return Response({"error": "Field 'hr_employee_id' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)

        user = HorillaUser.objects.select_for_update().filter(hr_employee_id=hr_id).first()
        if user is None:
            return Response({"skipped": True, "reason": "Belum punya akun CRM."})
        if request.data.get("hanya_lihat"):
            return Response({"ada": True, "username": user.username, "aktif": user.is_active})
        if not user.is_active:
            return Response({"skipped": True, "reason": "Akun CRM nonaktif, tidak diubah.", "username": user.username})

        username = str(request.data.get("username") or "").strip().lower()
        password = request.data.get("password")
        if not POLA_USERNAME.fullmatch(username):
            return Response({"error": "Format username tidak valid."}, status=status.HTTP_400_BAD_REQUEST)
        if password is not None and len(str(password)) < 8:
            return Response({"error": "Password awal minimal 8 karakter."}, status=status.HTTP_400_BAD_REQUEST)
        if HorillaUser.objects.filter(username=username).exclude(pk=user.pk).exists():
            return Response(
                {"username_terpakai": True, "error": f"Username '{username}' sudah dipakai akun lain di CRM."},
                status=status.HTTP_409_CONFLICT,
            )

        user.username = username
        sandi_diubah = False
        if password and user.has_usable_password():
            user.set_password(str(password))
            sandi_diubah = True
        user.save()
        return Response({"username": user.username, "sandi_diubah": sandi_diubah})
