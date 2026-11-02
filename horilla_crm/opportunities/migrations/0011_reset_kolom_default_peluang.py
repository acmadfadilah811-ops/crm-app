# Tidak melakukan apa pun. Percobaan pertama mereset kolom daftar Peluang salah menyaring (url_name dan context
# tertukar) dan sudah terlanjur terpasang di produksi tanpa efek. Logika yang benar ada di 0012.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0010_sumber_peluang_kasir'),
    ]

    operations = []
