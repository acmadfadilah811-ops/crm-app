"""Tes kredensial OAuth Google bersama (satu klien untuk semua pengguna)."""

from django.test import SimpleTestCase, override_settings

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
