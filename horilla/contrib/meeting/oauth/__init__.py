"""Pembantu bersama untuk alur OAuth penyedia rapat (Zoom, Teams)."""


def public_absolute_uri(request, path):
    """
    Alamat lengkap publik untuk sebuah path, selalu https di domain publik.

    CRM berjalan di belakang proxy HTTPS dan Django tidak memakai X-Forwarded-Proto, sehingga
    request.build_absolute_uri() menghasilkan http://. Penyedia OAuth menolaknya karena alamat
    pengalihan yang didaftarkan memakai https://.
    """
    uri = request.build_absolute_uri(path)
    if not uri.startswith("http://"):
        return uri
    host = request.get_host().split(":")[0].lower()
    forwarded = request.headers.get("X-Forwarded-Proto", "").split(",")[0].strip().lower()
    lokal = host in ("localhost", "0.0.0.0") or host.startswith("127.") or host.endswith(".local")
    if forwarded == "https" or not lokal:
        return "https://" + uri[len("http://"):]
    return uri
