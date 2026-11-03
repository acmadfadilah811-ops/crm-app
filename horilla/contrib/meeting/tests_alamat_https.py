"""Tes alamat pengalihan OAuth Zoom dan Teams: https di domain publik."""

from django.test import RequestFactory, SimpleTestCase, override_settings

from horilla.contrib.meeting.oauth.teams import _get_redirect_uri as teams_redirect
from horilla.contrib.meeting.oauth.zoom import _get_redirect_uri as zoom_redirect


@override_settings(ALLOWED_HOSTS=["*"])
class AlamatPengalihanRapatTests(SimpleTestCase):
    def _req(self, host):
        return RequestFactory().get("/", HTTP_HOST=host)

    def test_zoom_https_di_domain_publik(self):
        self.assertEqual(
            zoom_redirect(self._req("crm.starphotoadvertising.com")),
            "https://crm.starphotoadvertising.com/meeting/zoom/callback/",
        )

    def test_teams_https_di_domain_publik(self):
        self.assertEqual(
            teams_redirect(self._req("crm.starphotoadvertising.com")),
            "https://crm.starphotoadvertising.com/meeting/teams/callback/",
        )

    def test_localhost_tetap_http(self):
        self.assertEqual(
            zoom_redirect(self._req("localhost:8000")),
            "http://localhost:8000/meeting/zoom/callback/",
        )
