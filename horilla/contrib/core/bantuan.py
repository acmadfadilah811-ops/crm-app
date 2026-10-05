"""Katalog Pusat Bantuan CRM (2026-10-05), padanan katalog ERP dan HR.

Satu entri = satu layanan: tata cara, halaman (nama URL Django, di-reverse saat
tampil), dan skenario UAT. Hanya layanan milik peran pengguna yang ditampilkan.
Tanpa AI. Ubah entri bila menu berubah.

Peran CRM:
- sales: semua akun
- pengelola: superuser atau punya hak lihat SEMUA peluang (SPV/Manager)
"""

from django.urls import NoReverseMatch, reverse

URL_ERP = "https://app.starphotoadvertising.com"
URL_HR = "https://hr.starphotoadvertising.com"

URUTAN_MODUL = ["Akun & Login", "Prospek & Peluang", "Order ke ERP", "Pelanggan", "Laporan & Target", "HR & ERP"]

SEMUA = ["sales", "pengelola"]
PENGELOLA = ["pengelola"]

KATALOG = [
    # ── Akun & Login
    {
        "id": "login",
        "modul": "Akun & Login",
        "judul": "Masuk ke CRM",
        "ringkas": "Username dan sandi sama dengan HR/mobile dan ERP.",
        "peran": SEMUA,
        "kata_kunci": ["login", "masuk", "terkunci"],
        "langkah": [
            "Buka halaman login CRM, isi username dan sandi.",
            "Salah sandi berulang kali membuat akun terkunci sementara; tunggu atau minta kode OTP pembuka kunci.",
        ],
        "halaman": "core:login",
        "uat": ["PRE-04", "AKS-03"],
    },
    {
        "id": "lupa-sandi",
        "modul": "Akun & Login",
        "judul": "Lupa kata sandi",
        "ringkas": "Membuat sandi baru lewat email.",
        "peran": SEMUA,
        "kata_kunci": ["lupa", "sandi", "password", "reset"],
        "langkah": [
            "Di halaman login pilih lupa kata sandi, isi username atau email, kirim.",
            "Buka tautan dari email terbaru dan isi sandi baru.",
            "Sandi baru juga berlaku di HR/mobile dan ERP.",
        ],
        "halaman": "core:forgot_password",
        "uat": ["AKS-05"],
    },
    {
        "id": "profil-sandi",
        "modul": "Akun & Login",
        "judul": "Profil, foto, dan ubah kata sandi",
        "ringkas": "Mengubah data profil, foto, dan sandi.",
        "peran": SEMUA,
        "kata_kunci": ["profil", "foto", "ubah sandi", "ganti password"],
        "langkah": [
            "Buka Profil Saya dari menu akun (pojok kanan atas).",
            "Ubah data atau foto profil lalu simpan. Foto ikut berganti di HR dan ERP.",
            "Untuk sandi pilih Ubah Kata Sandi; sandi baru juga berlaku di HR dan ERP.",
        ],
        "halaman": "core:my_profile_view",
        "uat": ["AKS-05", "SEC-05"],
    },
    # ── Prospek & Peluang
    {
        "id": "prospek",
        "modul": "Prospek & Peluang",
        "judul": "Catat prospek dan follow-up",
        "ringkas": "Mencatat calon pelanggan dan status tindak lanjutnya.",
        "peran": SEMUA,
        "kata_kunci": ["prospek", "lead", "follow up", "calon pelanggan"],
        "langkah": [
            "Buka Prospek, tekan Buat (Baru).",
            "Isi nama, kontak, sumber, dan kebutuhan, lalu Simpan.",
            "Perbarui status prospek setiap kali follow-up.",
        ],
        "halaman": "leads:leads_view",
        "uat": ["E2E-03"],
    },
    {
        "id": "konversi",
        "modul": "Prospek & Peluang",
        "judul": "Ubah prospek menjadi peluang",
        "ringkas": "Prospek yang serius diubah menjadi Peluang (beserta akun dan kontak).",
        "peran": SEMUA,
        "kata_kunci": ["konversi", "convert", "peluang", "opportunity"],
        "langkah": [
            "Buka detail prospek, tekan Konversi.",
            "Periksa akun, kontak, dan peluang yang akan dibuat, lalu simpan.",
            "Lanjutkan di menu Peluang.",
        ],
        "halaman": "leads:leads_view",
        "uat": ["E2E-03"],
    },
    {
        "id": "peluang",
        "modul": "Prospek & Peluang",
        "judul": "Kelola peluang penjualan",
        "ringkas": "Memindahkan peluang antar tahap sampai menang atau kalah.",
        "peran": SEMUA,
        "kata_kunci": ["peluang", "opportunity", "pipeline", "tahap", "deal"],
        "langkah": [
            "Buka Peluang. Tampilan kanban memperlihatkan tahap tiap peluang.",
            "Geser kartu atau ubah Tahap di detail peluang sesuai perkembangan.",
            "Catat kegiatan (panggilan, rapat, tugas) di detail peluang.",
        ],
        "halaman": "opportunities:opportunities_view",
        "uat": ["E2E-03"],
    },
    {
        "id": "kampanye",
        "modul": "Prospek & Peluang",
        "judul": "Kampanye pemasaran",
        "ringkas": "Mencatat campaign dan menghubungkannya dengan prospek.",
        "peran": SEMUA,
        "kata_kunci": ["kampanye", "campaign", "promosi", "marketing"],
        "langkah": ["Buka Kampanye, tekan Buat.", "Isi nama, periode, dan anggaran, lalu Simpan. Hubungkan prospek ke kampanye ini."],
        "halaman": "campaigns:campaign_view",
        "uat": ["E2E-03"],
    },
    {
        "id": "kegiatan",
        "modul": "Prospek & Peluang",
        "judul": "Kegiatan: tugas, panggilan, rapat",
        "ringkas": "Jadwal dan catatan aktivitas penjualan.",
        "peran": SEMUA,
        "kata_kunci": ["kegiatan", "tugas", "panggilan", "rapat", "aktivitas", "jadwal"],
        "langkah": ["Buka Kegiatan.", "Buat tugas, panggilan, atau rapat dan tautkan ke prospek/peluang terkait."],
        "halaman": "activity:activity_view",
        "uat": [],
    },
    # ── Order ke ERP
    {
        "id": "buat-order",
        "modul": "Order ke ERP",
        "judul": "Buat order ke ERP dari peluang",
        "ringkas": "Order dari peluang masuk Antrean Online & Offline kasir ERP.",
        "peran": SEMUA,
        "kata_kunci": ["order", "pesanan", "buat order", "erp", "bintang", "kasir"],
        "langkah": [
            "Buka detail peluang, tab Order Bintang, tekan + Buat Order.",
            "Cari produk ERP, isi jumlah, periksa total, lalu kirim.",
            "Order masuk antrean kasir ERP sebagai draft untuk dibayar dan diterbitkan SPK-nya.",
        ],
        "halaman": "opportunities:opportunities_view",
        "uat": ["E2E-03"],
        "catatan": "Order tercatat atas nama Sales pembuatnya.",
    },
    {
        "id": "order-saya",
        "modul": "Order ke ERP",
        "judul": "Pantau status order (Order Saya)",
        "ringkas": "Melihat status order yang sudah dikirim ke ERP tanpa bertanya ke kasir.",
        "peran": SEMUA,
        "kata_kunci": ["order saya", "status order", "pantau", "produksi"],
        "langkah": [
            "Buka Order Saya.",
            "Lihat status pembayaran dan produksi tiap order. SPV/Manager melihat order semua Sales.",
        ],
        "halaman": "opportunities:order_saya",
        "uat": ["E2E-03"],
    },
    # ── Pelanggan
    {
        "id": "akun-kontak",
        "modul": "Pelanggan",
        "judul": "Akun dan kontak pelanggan",
        "ringkas": "Data perusahaan (Akun) dan orang yang dihubungi (Kontak).",
        "peran": SEMUA,
        "kata_kunci": ["akun", "kontak", "pelanggan", "perusahaan", "customer"],
        "langkah": [
            "Buka Akun untuk data perusahaan/pelanggan, atau Kontak untuk orangnya.",
            "Cari dulu sebelum membuat baru supaya pelanggan tidak dobel.",
        ],
        "halaman": "accounts:accounts_view",
        "uat": ["E2E-03"],
    },
    # ── Laporan & Target
    {
        "id": "target-sales",
        "modul": "Laporan & Target",
        "judul": "Target sales",
        "ringkas": "Melihat target dan capaian penjualan.",
        "peran": SEMUA,
        "kata_kunci": ["target", "capaian", "kpi"],
        "langkah": ["Buka Target Sales.", "Sales melihat targetnya sendiri; pengelola dapat membuat dan mengubah target tiap Sales."],
        "halaman": "opportunities:target_sales",
        "uat": [],
    },
    {
        "id": "laporan-sales",
        "modul": "Laporan & Target",
        "judul": "Laporan sales",
        "ringkas": "Rekap penjualan per Sales dari data order ERP.",
        "peran": PENGELOLA,
        "kata_kunci": ["laporan", "rekap", "penjualan", "sales"],
        "langkah": ["Buka Laporan Sales.", "Pilih periode untuk melihat rekap per Sales."],
        "halaman": "opportunities:laporan_sales",
        "uat": ["E2E-03"],
    },
    {
        "id": "dasbor-laporan",
        "modul": "Laporan & Target",
        "judul": "Dasbor, laporan, dan perkiraan",
        "ringkas": "Grafik pipeline, laporan kustom, dan perkiraan penjualan.",
        "peran": PENGELOLA,
        "kata_kunci": ["dasbor", "dashboard", "laporan", "perkiraan", "forecast", "pipeline"],
        "langkah": ["Buka Dasbor untuk grafik ringkas.", "Buka Laporan untuk laporan kustom, atau Perkiraan untuk proyeksi penjualan."],
        "halaman": "reports:reports_list_view",
        "uat": ["E2E-03"],
    },
    # ── HR & ERP
    {
        "id": "hr",
        "modul": "HR & ERP",
        "judul": "Absen, cuti, lembur, slip gaji (HR)",
        "ringkas": "Urusan kepegawaian ada di aplikasi HR dan mobile.",
        "peran": SEMUA,
        "kata_kunci": ["hr", "absen", "cuti", "lembur", "slip gaji"],
        "langkah": ["Buka HR di browser atau aplikasi mobile, login dengan akun yang sama.", "Tekan tombol Bantuan di HR untuk tata caranya."],
        "url_luar": URL_HR,
        "uat": [],
    },
    {
        "id": "erp",
        "modul": "HR & ERP",
        "judul": "Kasir, produksi, dan keuangan (ERP)",
        "ringkas": "Pembayaran dan produksi order dikerjakan di ERP.",
        "peran": PENGELOLA,
        "kata_kunci": ["erp", "kasir", "produksi", "spk"],
        "langkah": ["Buka ERP dan login dengan akun yang sama.", "Tekan tombol Bantuan di ERP untuk tata cara sesuai peran Anda di sana."],
        "url_luar": URL_ERP,
        "uat": [],
    },
]


def peran_pengguna(user):
    if not getattr(user, "is_authenticated", False):
        return []
    peran = ["sales"]
    if user.is_superuser or user.has_perm("opportunities.view_opportunity"):
        peran.append("pengelola")
    return peran


def katalog_untuk(user):
    """Entri katalog yang boleh dilihat pengguna, dengan URL sudah di-reverse."""
    peran = set(peran_pengguna(user))
    hasil = []
    for entri in KATALOG:
        if not peran.intersection(entri["peran"]):
            continue
        item = {k: v for k, v in entri.items() if k not in ("peran", "halaman")}
        if entri.get("halaman"):
            try:
                item["url"] = reverse(entri["halaman"])
            except NoReverseMatch:
                item["url"] = ""
        hasil.append(item)
    return hasil
