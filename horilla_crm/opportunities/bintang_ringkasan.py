"""Ringkasan jelas untuk Peluang (Opportunity) yang datang dari order ERP (2026-11-02).

Sebelumnya Peluang hasil sinkron hanya bernama "Penjualan StarFoto 12345" dengan nilai dan tanggal, tanpa
tahu siapa pelanggannya, apa yang dibeli, sudah dibayar berapa, dan apa langkah berikutnya. Modul ini
menyusun nama, deskripsi, jumlah barang, dan "langkah berikutnya" dari rincian order yang dikirim ERP
(blok `sale`). Fungsi murni tanpa akses database supaya mudah diuji."""

from decimal import Decimal, InvalidOperation

MAKS_DESKRIPSI = 4000
MAKS_ITEM = 40


def rupiah(nilai):
    """12500 -> 'Rp. 12.500' (pemisah ribuan titik, tanpa desimal)."""
    try:
        angka = int(Decimal(str(nilai or 0)).quantize(Decimal("1")))
    except (InvalidOperation, ValueError):
        angka = 0
    return "Rp. " + f"{angka:,}".replace(",", ".")


def _angka(nilai):
    try:
        return Decimal(str(nilai))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


def _tampil_qty(nilai):
    angka = _angka(nilai)
    teks = format(angka.normalize(), "f")
    return teks.rstrip("0").rstrip(".") if "." in teks else teks


def jumlah_barang(items):
    return sum((_angka(i.get("qty")) for i in items if isinstance(i, dict)), Decimal("0"))


def nama_peluang(sale, nomor, unit):
    pelanggan = str(sale.get("pelanggan") or "").strip()
    dasar = f"{unit} {nomor}".strip()
    return (f"{pelanggan} - {dasar}" if pelanggan else f"Penjualan {dasar}")[:120]


def langkah_berikutnya(sale, lunas):
    if lunas:
        return "Lunas - tidak ada tagihan tersisa"
    sisa = int(_angka(sale.get("sisa_tagihan")))
    status = str(sale.get("status_order") or "").strip()
    teks = f"Menunggu pelunasan sisa {rupiah(sisa)}" if sisa > 0 else "Menunggu pembayaran"
    return (f"{teks} ({status})" if status else teks)[:255]


def deskripsi(sale, nomor, unit, nomor_wa, lunas):
    """Teks rincian untuk kolom Deskripsi Peluang."""
    total = _angka(sale.get("total"))
    dp = _angka(sale.get("dp_dibayar"))
    sisa = _angka(sale.get("sisa_tagihan"))
    baris = [
        f"Order ERP: {nomor}" + (f" ({unit})" if unit else ""),
        f"Pelanggan: {sale.get('pelanggan') or '-'}" + (f" - WA {nomor_wa}" if nomor_wa else ""),
    ]
    if sale.get("dilayani_oleh"):
        baris.append(f"Dilayani oleh: {sale['dilayani_oleh']}")
    if sale.get("status_order"):
        baris.append(f"Status order: {sale['status_order']}")
    items = [i for i in (sale.get("items") or []) if isinstance(i, dict)]
    if items:
        baris.append("")
        baris.append("Rincian pesanan:")
        for i in items[:MAKS_ITEM]:
            baris.append(f"- {i.get('nama') or 'Item'} x {_tampil_qty(i.get('qty'))} = {rupiah(i.get('subtotal'))}")
        if len(items) > MAKS_ITEM:
            baris.append(f"- ... dan {len(items) - MAKS_ITEM} item lainnya")
    baris += [
        "",
        f"Total tagihan: {rupiah(total)}",
        f"Sudah dibayar: {rupiah(dp if not lunas else total)}",
        f"Sisa tagihan: {rupiah(0 if lunas else sisa)}",
    ]
    if sale.get("metode_pembayaran"):
        baris.append(f"Metode pembayaran: {sale['metode_pembayaran']}")
    if sale.get("catatan"):
        baris += ["", f"Catatan pelanggan: {sale['catatan']}"]
    return "\n".join(baris)[:MAKS_DESKRIPSI]


def susun(sale, nomor, unit, nomor_wa, lunas):
    """Kumpulan nilai field Peluang dari satu order ERP."""
    items = [i for i in (sale.get("items") or []) if isinstance(i, dict)]
    hasil = {
        "name": nama_peluang(sale, nomor, unit),
        "description": deskripsi(sale, nomor, unit, nomor_wa, lunas),
        "next_step": langkah_berikutnya(sale, lunas),
    }
    if items:
        hasil["quantity"] = jumlah_barang(items).quantize(Decimal("0.01"))
    return hasil
