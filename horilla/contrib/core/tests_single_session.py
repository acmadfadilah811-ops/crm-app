"""UAT poin 29: satu akun tidak bisa dipakai login di banyak perangkat
sekaligus. LoginUserView (horilla/contrib/core/views/core.py) memanggil
login_lock.matikan_sesi_lain() tepat sebelum django.contrib.auth.login() --
semua Session Django lain milik user yang sama dihapus, supaya perangkat/
browser lama langsung ter-logout. Pola sama dengan Bintang & HR."""

from django.core.cache import cache as default_cache, caches
from django.test import Client, TestCase

from horilla.contrib.core.models.user import HorillaUser

SANDI = "SandiDuaDevice2026x"
UA = {"HTTP_USER_AGENT": "pytest"}


class SatuAkunSatuSesiTests(TestCase):
    def setUp(self):
        caches["login_lock"].clear()
        self.addCleanup(caches["login_lock"].clear)
        default_cache.clear()
        self.addCleanup(default_cache.clear)
        self.user = HorillaUser.objects.create(
            username="dua_device_crm", email="dua_device_crm@test.horilla"
        )
        self.user.set_password(SANDI)
        self.user.save()

    def login(self, client, username="dua_device_crm", sandi=SANDI):
        return client.post("/login/", {"username": username, "password": sandi, "next": "/"})

    def test_login_kedua_mencabut_sesi_pertama(self):
        device1 = Client(**UA)
        device2 = Client(**UA)

        self.login(device1)
        self.assertEqual(device1.session.get("_auth_user_id"), str(self.user.pk))

        self.login(device2)

        self.assertIsNone(device1.session.get("_auth_user_id"))
        self.assertEqual(device2.session.get("_auth_user_id"), str(self.user.pk))

    def test_login_baru_tidak_mencabut_sesi_user_lain(self):
        other = HorillaUser.objects.create(username="user_lain_crm", email="user_lain_crm@test.horilla")
        other.set_password("SandiLain2026x")
        other.save()

        device_other = Client(**UA)
        self.login(device_other, username="user_lain_crm", sandi="SandiLain2026x")
        self.assertEqual(device_other.session.get("_auth_user_id"), str(other.pk))

        device_self = Client(**UA)
        self.login(device_self)

        self.assertEqual(device_other.session.get("_auth_user_id"), str(other.pk))
