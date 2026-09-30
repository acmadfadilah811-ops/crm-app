"""POST /api/bridge/hr-employee-sandi/  (X-Api-Key = HR_BRIDGE_API_KEY)

  {"hr_employee_id": 42, "password_hash": "pbkdf2_sha256$..."}
Dipanggil HR saat sandi karyawan diganti di HR/ERP. Menyalin hash ke akun CRM.
Akun tanpa sandi dilewati.
"""
from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.core.sinkron_sandi import hash_valid, terapkan_hash

from .hr_bridge import HRBridgeThrottle
from .hr_organisasi import _cek_api_key


class HRBridgeSandiView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    @transaction.atomic
    def post(self, request):
        auth_error = _cek_api_key(request)
        if auth_error:
            return auth_error
        hr_id = request.data.get("hr_employee_id")
        encoded = request.data.get("password_hash")
        if not hr_id:
            return Response({"error": "Field 'hr_employee_id' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        if not hash_valid(encoded):
            return Response({"error": "Format hash sandi tidak valid."}, status=status.HTTP_400_BAD_REQUEST)
        user = HorillaUser.objects.select_for_update().filter(hr_employee_id=hr_id).first()
        if user is None:
            return Response({"skipped": True, "reason": "Belum punya akun CRM."})
        if not user.has_usable_password():
            return Response({"skipped": True, "reason": "Akun tanpa sandi."})
        terapkan_hash(user, encoded)
        return Response({"diterapkan": True})
