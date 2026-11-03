"""Tes kredensial OAuth Google bersama (satu klien untuk semua pengguna)."""

from django.test import RequestFactory, SimpleTestCase, override_settings

from horilla.contrib.calendar.google_calendar.views import _public_absolute_uri, _redirect_uri_for
from horilla.contrib.calendar.models import GoogleCalendarConfig

PILIHAN_PENGGUNA = {"web": {"client_id": "id-pengguna", "client_secret": "rahasia-pengguna"}}


class KredensialGoogleBersamaTests(SimpleTestCase):
    """Pengguna tanpa unggahan sendiri memakai kredensial perusahaan; unggahan sendiri tetap diutamakan."""

    @override_settings(GOOGLE_CALENDAR_CLIENT_ID="", GOOGLE_CALENDAR_CLIENT_SECRET="")
    def test_tanpa_kredensial_apa_pun_belum_siap(self):
        cfg = GoogleCalendarConfig()
        self.assertFalse(cfg.is_configured())
        self.assertEqual(cfg.get_client_id(), "")

    @override_settings(GOOGLE_CALENDAR_CLIENT_ID="id-bersama", GOOGLE_CALENDAR_CLIENT_SECRET="rahasia-bersama")
    def test_kredensial_bersama_membuat_pengguna_langsung_siap(self):
        cfg = GoogleCalendarConfig()
        self.assertTrue(cfg.is_configured())
        self.assertEqual(cfg.get_client_id(), "id-bersama")
        self.assertEqual(cfg.get_client_secret(), "rahasia-bersama")
        # alamat Google bawaan dipakai karena kredensial bersama hanya berisi id dan rahasia
        self.assertIn("accounts.google.com", cfg.get_auth_uri())
        self.assertIn("googleapis.com", cfg.get_token_uri())

    @override_settings(GOOGLE_CALENDAR_CLIENT_ID="id-bersama", GOOGLE_CALENDAR_CLIENT_SECRET="rahasia-bersama")
    def test_unggahan_pengguna_diutamakan(self):
        cfg = GoogleCalendarConfig(credentials_json=PILIHAN_PENGGUNA)
        self.assertEqual(cfg.get_client_id(), "id-pengguna")
        self.assertEqual(cfg.get_client_secret(), "rahasia-pengguna")

    @override_settings(GOOGLE_CALENDAR_CLIENT_ID="id-bersama", GOOGLE_CALENDAR_CLIENT_SECRET="")
    def test_setengah_terisi_tidak_dianggap_siap(self):
        self.assertFalse(GoogleCalendarConfig().is_configured())


CALLBACK = "calendar:google_calendar_callback"


@override_settings(ALLOWED_HOSTS=["*"], DEBUG=False)
class AlamatPublikGoogleTests(SimpleTestCase):
    """Alamat callback/webhook yang dikirim ke Google harus https agar cocok dengan klien OAuth."""

    def _alamat(self, host, **header):
        request = RequestFactory().get("/", HTTP_HOST=host, **header)
        return _public_absolute_uri(request, CALLBACK)

    def test_domain_publik_dinaikkan_ke_https(self):
        self.assertEqual(
            self._alamat("crm.starphotoadvertising.com"),
            "https://crm.starphotoadvertising.com/calendar/google-calendar/callback/",
        )

    def test_header_proxy_https_dihormati(self):
        self.assertTrue(self._alamat("127.0.0.1:8000", HTTP_X_FORWARDED_PROTO="https").startswith("https://"))

    def test_localhost_tetap_http(self):
        self.assertTrue(self._alamat("localhost:8000").startswith("http://localhost:8000/"))

    @override_settings(DEBUG=True)
    def test_mode_debug_di_domain_publik_tetap_https(self):
        self.assertTrue(self._alamat("dev.example.com").startswith("https://"))

    def test_alamat_http_lama_tersimpan_dinaikkan(self):
        request = RequestFactory().get("/", HTTP_HOST="crm.starphotoadvertising.com")
        cfg = GoogleCalendarConfig(redirect_uri="http://crm.starphotoadvertising.com/calendar/google-calendar/callback/")
        self.assertEqual(
            _redirect_uri_for(cfg, request),
            "https://crm.starphotoadvertising.com/calendar/google-calendar/callback/",
        )

    def test_alamat_tersimpan_milik_pengguna_lain_tetap_dipakai(self):
        request = RequestFactory().get("/", HTTP_HOST="crm.starphotoadvertising.com")
        cfg = GoogleCalendarConfig(redirect_uri="https://lain.example.com/callback/")
        self.assertEqual(_redirect_uri_for(cfg, request), "https://lain.example.com/callback/")
