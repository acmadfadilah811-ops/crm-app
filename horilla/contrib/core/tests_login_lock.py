"""Penguncian login CRM: 3 gagal untuk (username, IP) -> kunci 10 menit; kunci IP
setelah 3 akun berbeda gagal dari 1 IP; OTP untuk membuka lebih cepat. Diseragamkan
dengan Bintang dan HR."""

import re
from unittest import mock

from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache as default_cache, caches
from django.test import Client, TestCase

from horilla.contrib.core import login_lock
from horilla.contrib.core.models.user import HorillaUser

SANDI = "SandiBenar2026x"
# Django test client tidak mengirim header User-Agent secara default (browser/app
# nyata selalu mengirim) -- login_history.post_login membacanya tanpa fallback.
UA = {"HTTP_USER_AGENT": "pytest"}


class LoginLockTests(TestCase):
    def setUp(self):
        caches["login_lock"].clear()
        self.addCleanup(caches["login_lock"].clear)
        default_cache.clear()   # cooldown kirim-OTP dipakai dari cache default, bukan login_lock
        self.addCleanup(default_cache.clear)
        self.client = Client(**UA)   # login_history.post_logout butuh User-Agent juga
        self.user = HorillaUser.objects.create(
            username="kunci.uji", email="kunci.uji@test.horilla"
        )
        self.user.set_password(SANDI)
        self.user.save()
        self.url = "/login/"

    def post(self, sandi, username="kunci.uji", ip="10.0.0.1", otp=None):
        data = {"username": username, "password": sandi, "next": "/"}
        if otp:
            data["otp"] = otp
        return self.client.post(self.url, data, HTTP_X_FORWARDED_FOR=ip)

    def pesan(self, response):
        return " ".join(str(m) for m in get_messages(response.wsgi_request))

    def masuk(self):
        return "_auth_user_id" in self.client.session

    def test_tiga_kali_salah_lalu_terkunci_walau_sandi_benar(self):
        self.assertIn("Sisa percobaan: 2", self.pesan(self.post("salah")))
        self.assertIn("Sisa percobaan: 1", self.pesan(self.post("salah")))
        self.assertIn("dikunci", self.pesan(self.post("salah")))
        r = self.post(SANDI)
        self.assertIn("dikunci", self.pesan(r))
        self.assertFalse(self.masuk())

    def test_dua_kali_salah_lalu_benar_berhasil_dan_hitungan_direset(self):
        self.post("salah")
        self.post("salah")
        self.post(SANDI)
        self.assertTrue(self.masuk())
        self.client.get("/logout/")
        self.post("salah")
        self.post("salah")
        self.post(SANDI)
        self.assertTrue(self.masuk())

    def test_kunci_per_username_dan_ip_ip_lain_tidak_ikut_terkunci(self):
        for _ in range(3):
            self.post("salah", ip="10.0.0.1")
        self.assertFalse(self.masuk())
        self.post(SANDI, ip="10.0.0.2")
        self.assertTrue(self.masuk())

    def test_username_tidak_ada_diperlakukan_sama_anti_enumerasi(self):
        for _ in range(3):
            self.post("x", username="hantu", ip="10.9.9.9")
        self.assertIn("dikunci", self.pesan(self.post("x", username="hantu", ip="10.9.9.9")))

    def test_sisa_waktu_kunci_maksimal_10_menit(self):
        for _ in range(3):
            self.post("salah")
        sisa = login_lock.sisa_waktu_kunci("kunci.uji", "10.0.0.1")
        self.assertGreater(sisa, 0)
        self.assertLessEqual(sisa, 600)

    def test_kunci_berakhir_setelah_masa_habis(self):
        for _ in range(3):
            self.post("salah")
        caches["login_lock"].clear()  # simulasi 10 menit berlalu
        self.post(SANDI)
        self.assertTrue(self.masuk())

    def test_cache_mati_login_tetap_berjalan_fail_open(self):
        with mock.patch.object(
            login_lock, "_cache", side_effect=RuntimeError("redis mati")
        ):
            self.post(SANDI)
        self.assertTrue(self.masuk())


class KunciIpDanOtpTests(TestCase):
    """IP yang gagal login ke >=3 akun BERBEDA diblokir; OTP membuka kunci akun
    sendiri saja tanpa membuka kunci IP untuk akun lain."""

    def setUp(self):
        caches["login_lock"].clear()
        self.addCleanup(caches["login_lock"].clear)
        default_cache.clear()   # cooldown kirim-OTP dipakai dari cache default, bukan login_lock
        self.addCleanup(default_cache.clear)
        self.client = Client(**UA)   # login_history.post_logout butuh User-Agent juga
        self.users = {}
        for u in ("ip_a", "ip_b", "ip_c", "ip_d"):
            user = HorillaUser.objects.create(username=u, email=f"{u}@test.horilla")
            user.set_password(SANDI + u)
            user.save()
            self.users[u] = user
        self.url = "/login/"

    def post(self, username, sandi, ip="9.9.9.9", otp=None):
        data = {"username": username, "password": sandi, "next": "/"}
        if otp:
            data["otp"] = otp
        return self.client.post(self.url, data, HTTP_X_FORWARDED_FOR=ip)

    def kirim_otp(self, username):
        self.client.post("/login/unlock-otp/", {"username": username})

    def masuk(self):
        return "_auth_user_id" in self.client.session

    def pesan(self, response):
        return " ".join(str(m) for m in get_messages(response.wsgi_request))

    def test_tiga_akun_berbeda_gagal_dari_satu_ip_mengunci_ip_itu(self):
        self.post("ip_a", "salah")
        self.post("ip_b", "salah")
        r = self.post("ip_c", "salah")
        self.assertIn("IP ini diblokir", self.pesan(r))

    def test_ip_terkunci_memblokir_akun_keempat_walau_sandi_benar_dan_belum_pernah_gagal(self):
        for u in ("ip_a", "ip_b", "ip_c"):
            self.post(u, "salah")
        r = self.post("ip_d", SANDI + "ip_d")   # sandi BENAR, belum pernah gagal
        self.assertIn("IP ini diblokir", self.pesan(r))
        self.assertFalse(self.masuk())

    def test_ip_berbeda_tidak_ikut_terkunci(self):
        for u in ("ip_a", "ip_b", "ip_c"):
            self.post(u, "salah", ip="9.9.9.9")
        r = self.post("ip_d", SANDI + "ip_d", ip="8.8.8.8")
        self.assertTrue(self.masuk())

    def test_otp_unlock_membuka_akun_sendiri_walau_ip_terkunci_tanpa_membuka_utk_akun_lain(self):
        for u in ("ip_a", "ip_b", "ip_c"):
            self.post(u, "salah")
        self.kirim_otp("ip_a")
        otp = self.ambil_otp()
        r = self.post("ip_a", SANDI + "ip_a", otp=otp)
        self.assertTrue(self.masuk())
        self.client.get("/logout/")
        r2 = self.post("ip_d", SANDI + "ip_d")   # akun lain tetap diblokir kunci IP
        self.assertIn("IP ini diblokir", self.pesan(r2))

    def test_otp_salah_tidak_membuka_kunci(self):
        for u in ("ip_a", "ip_b", "ip_c"):
            self.post(u, "salah")
        self.kirim_otp("ip_a")
        r = self.post("ip_a", SANDI + "ip_a", otp="000000")
        self.assertFalse(self.masuk())

    def test_otp_sekali_pakai(self):
        for u in ("ip_a", "ip_b", "ip_c"):
            self.post(u, "salah")
        self.kirim_otp("ip_a")
        otp = self.ambil_otp()
        self.post("ip_a", SANDI + "ip_a", otp=otp)
        self.assertTrue(self.masuk())
        self.client.get("/logout/")
        r = self.post("ip_b", SANDI + "ip_b", otp=otp)   # otp lama dipakai lagi
        self.assertFalse(self.masuk())

    def test_unlock_otp_request_akun_tidak_ada_tetap_respons_generik(self):
        r = self.client.post("/login/unlock-otp/", {"username": "hantu_tidak_ada"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Jika akun ada", r.content.decode())

    def test_gagal_akun_sama_berkali_tidak_menghitung_sbg_akun_berbeda(self):
        for _ in range(5):
            self.post("ip_a", "salah")
        r = self.post("ip_b", SANDI + "ip_b")
        self.assertTrue(self.masuk())

    def ambil_otp(self):
        return re.search(r"KODE: (\d{6})", mail.outbox[-1].body).group(1)
