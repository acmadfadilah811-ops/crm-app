"""Penguncian login sementara (diseragamkan dengan Bintang & HR).

Aturan: MAKS_GAGAL_LOGIN kali gagal berturut-turut untuk kombinasi (username, IP)
mengunci login selama DURASI_KUNCI_LOGIN detik. Kunci per (username, IP) -- sama
dengan HR (django-axes) -- agar orang lain tidak bisa mengunci akun sengaja dari IP lain
dan satu IP bersama tidak mengunci semua orang.

Sebelumnya: kunci hanya per IP (5 gagal, 15 menit) dengan cache memori per proses
(2 worker gunicorn -> hitungan tidak dibagi). Sekarang memakai cache alias
``login_lock`` (Redis bila REDIS_URL ada, sehingga dibagi antar worker).

Bila cache gagal (mis. Redis mati), login TIDAK ikut mati: penguncian dilewati
(fail-open) dan kejadiannya dicatat di log.

Lapisan kedua -- kunci IP (sama dengan Bintang): satu IP yang gagal login ke
MAKS_AKUN_BERBEDA_PER_IP akun BERBEDA dalam DURASI_KUNCI_IP diblokir dari login akun
manapun. Kunci per-(username, IP) di atas TIDAK menghentikan penyerang yang mencoba
banyak akun berbeda (di bawah ambang per akun) dari satu IP; kunci IP ini menutup celah
itu. OTP_UNLOCK_TTL adalah OTP terpisah (bukan reset password) yang membuktikan pemohon
menguasai email akun yang diserang, sehingga bisa membuka kunci akunnya sendiri lebih
cepat tanpa membuka kunci IP untuk akun lain."""

import logging
import secrets
import time

from django.core.cache import caches

logger = logging.getLogger(__name__)

MAKS_GAGAL_LOGIN = 3
DURASI_KUNCI_LOGIN = 10 * 60
MAKS_AKUN_BERBEDA_PER_IP = 3
DURASI_KUNCI_IP = 10 * 60
OTP_UNLOCK_TTL = 5 * 60


def _cache():
    return caches["login_lock"]


def _kunci(username, ip):
    return f"login_lock:{str(username or '').strip().lower()}:{ip}"


def sisa_waktu_kunci(username, ip):
    """Detik tersisa masa kunci (0 bila tidak terkunci)."""
    try:
        waktu_kunci = _cache().get(f"{_kunci(username, ip)}:locked")
    except Exception:  # noqa: BLE001 -- cache mati tidak boleh mematikan login
        logger.warning("login_lock: cache tidak tersedia (cek kunci)", exc_info=True)
        return 0
    if waktu_kunci is None:
        return 0
    try:
        return max(1, int(DURASI_KUNCI_LOGIN - (time.time() - float(waktu_kunci))))
    except (TypeError, ValueError):
        return DURASI_KUNCI_LOGIN


def catat_gagal(username, ip):
    """Mencatat satu kegagalan. Mengembalikan (jumlah_gagal, terkunci_sekarang)."""
    try:
        cache = _cache()
        key = _kunci(username, ip)
        gagal = int(cache.get(key, 0) or 0) + 1
        cache.set(key, gagal, DURASI_KUNCI_LOGIN)
        terkunci = gagal >= MAKS_GAGAL_LOGIN
        if terkunci:
            cache.set(f"{key}:locked", time.time(), DURASI_KUNCI_LOGIN)
            logger.warning("Login dikunci %ss: username=%s ip=%s", DURASI_KUNCI_LOGIN, username, ip)
        return gagal, terkunci
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (catat gagal)", exc_info=True)
        return 0, False


def reset(username, ip):
    try:
        cache = _cache()
        key = _kunci(username, ip)
        cache.delete(key)
        cache.delete(f"{key}:locked")
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (reset)", exc_info=True)


def format_menit_detik(detik):
    detik = max(0, int(detik))
    return f"{detik // 60}:{detik % 60:02d}"


def _ip_key(ip):
    return f"login_ip_lock:{ip}"


def sisa_waktu_kunci_ip(ip):
    """Detik tersisa masa kunci IP (0 bila tidak terkunci)."""
    try:
        waktu_kunci = _cache().get(f"{_ip_key(ip)}:locked")
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (cek kunci ip)", exc_info=True)
        return 0
    if waktu_kunci is None:
        return 0
    try:
        return max(1, int(DURASI_KUNCI_IP - (time.time() - float(waktu_kunci))))
    except (TypeError, ValueError):
        return DURASI_KUNCI_IP


def catat_gagal_ip(ip, username):
    """Mencatat username yang gagal dari IP ini. True bila IP baru saja terkunci."""
    try:
        cache = _cache()
        key = _ip_key(ip)
        usernames = cache.get(key) or set()
        usernames.add(str(username or "").strip().lower())
        cache.set(key, usernames, DURASI_KUNCI_IP)
        if len(usernames) >= MAKS_AKUN_BERBEDA_PER_IP:
            cache.set(f"{key}:locked", time.time(), DURASI_KUNCI_IP)
            logger.warning("Login IP dikunci %ss: ip=%s akun=%s", DURASI_KUNCI_IP, ip, sorted(usernames))
            return True
        return False
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (catat gagal ip)", exc_info=True)
        return False


def _otp_key(username):
    return f"login_unlock_otp:{str(username or '').strip().lower()}"


def simpan_otp_unlock(username):
    """Membuat & menyimpan OTP baru untuk membuka kunci login username ini."""
    otp = str(secrets.SystemRandom().randint(100000, 999999))
    try:
        _cache().set(_otp_key(username), {"otp": otp, "attempts": 0}, OTP_UNLOCK_TTL)
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (simpan otp)", exc_info=True)
        return None
    return otp


def verifikasi_otp_unlock(username, otp_input):
    """OTP sekali pakai; benar -> dihapus & True. Salah -> dihitung, habis 5x -> dihapus."""
    try:
        cache = _cache()
        key = _otp_key(username)
        state = cache.get(key)
        if not state:
            return False
        if not secrets.compare_digest(str(state.get("otp", "")), str(otp_input or "")):
            state["attempts"] = int(state.get("attempts", 0)) + 1
            if state["attempts"] >= 5:
                cache.delete(key)
            else:
                cache.set(key, state, OTP_UNLOCK_TTL)
            return False
        cache.delete(key)
        return True
    except Exception:  # noqa: BLE001
        logger.warning("login_lock: cache tidak tersedia (verifikasi otp)", exc_info=True)
        return False


def matikan_sesi_lain(user):
    """UAT poin 29: satu akun tidak boleh login dari banyak perangkat sekaligus.
    Dipanggil TEPAT SEBELUM django.contrib.auth.login() berhasil membuat sesi
    baru -- semua Session Django lain yang masih menunjuk ke user ini dihapus,
    supaya perangkat/browser lama langsung ter-logout. Pola sama persis dengan
    Horilla HR (base/login_lock.py)."""
    from django.contrib.sessions.models import Session
    from django.utils import timezone

    target_id = str(user.pk)
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if data.get("_auth_user_id") == target_id:
            session.delete()
