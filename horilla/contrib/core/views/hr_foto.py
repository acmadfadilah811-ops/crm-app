"""POST /api/bridge/hr-employee-foto/  (X-Api-Key = HR_BRIDGE_API_KEY)

  {"hr_employee_id": 42, "foto": "<base64 JPEG/PNG/WEBP, maks 1 MB>"}
  {"hr_employee_id": 42, "hapus": true}
Dipanggil HR saat foto profil karyawan berubah di HR/ERP. Logika di sinkron_foto.py.
"""
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from horilla.contrib.core.models.user import HorillaUser
from horilla.contrib.core.sinkron_foto import baca_payload_foto, terapkan_foto

from .hr_bridge import HRBridgeThrottle
from .hr_organisasi import _cek_api_key


class HRBridgeFotoView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [HRBridgeThrottle]

    def post(self, request):
        auth_error = _cek_api_key(request)
        if auth_error:
            return auth_error
        hr_id = request.data.get("hr_employee_id")
        if not hr_id:
            return Response({"error": "Field 'hr_employee_id' wajib diisi."}, status=status.HTTP_400_BAD_REQUEST)
        ok, data, pesan = baca_payload_foto(request.data)
        if not ok:
            return Response({"error": pesan}, status=status.HTTP_400_BAD_REQUEST)
        user = HorillaUser.objects.filter(hr_employee_id=hr_id).first()
        if user is None:
            return Response({"skipped": True, "reason": "Belum punya akun CRM."})
        terapkan_foto(user, data)
        return Response({"diterapkan": True})
