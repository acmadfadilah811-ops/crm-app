"""{% pusat_bantuan %} -- tombol Bantuan + katalog sesuai peran (lihat horilla/contrib/core/bantuan.py)."""

from django import template

from horilla.contrib.core.bantuan import URUTAN_MODUL, katalog_untuk

register = template.Library()


@register.inclusion_tag("bantuan/widget.html", takes_context=True)
def pusat_bantuan(context):
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"tampil": False}
    return {
        "tampil": True,
        "data_bantuan": {"modul": URUTAN_MODUL, "layanan": katalog_untuk(user)},
    }
