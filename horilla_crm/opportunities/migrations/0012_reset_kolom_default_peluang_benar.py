# Daftar Peluang kini menampilkan Pemilik, Langkah Berikutnya, dan Sumber Prospek (2026-11-02). Kolom daftar
# disimpan per pengguna (ListColumnVisibility), jadi pengguna yang hanya memegang salinan kolom bawaan lama
# tidak akan melihat kolom baru. Migrasi ini menghapus HANYA salinan yang persis sama dengan bawaan lama;
# pilihan kolom yang sudah disesuaikan pengguna tidak disentuh. Bawaan baru dibuat ulang otomatis saat daftar
# dibuka.
#
# Menggantikan 0011, yang salah menyaring (url_name dan context tertukar sehingga tidak menghapus apa pun).

from django.db import migrations

KOLOM_BAWAAN_LAMA = [
    ['Opportunity Name', 'name'],
    ['Amount', 'amount'],
    ['Close Date', 'close_date'],
    ['Stage', 'stage'],
    ['Type', 'opportunity_type'],
    ['Primary Campaign Source', 'primary_campaign_source'],
]


def hapus_salinan_bawaan_lama(apps, schema_editor):
    ListColumnVisibility = apps.get_model('core', 'ListColumnVisibility')
    baris = ListColumnVisibility._base_manager.filter(
        app_label='opportunities',
        model_name='Opportunity',
        url_name='opportunities_list',
        context='crm_opportunities_opportunities-view',
    )
    ids = [b.pk for b in baris if b.visible_fields == KOLOM_BAWAAN_LAMA]
    if ids:
        ListColumnVisibility._base_manager.filter(pk__in=ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0011_reset_kolom_default_peluang'),
        ('core', '0011_horillauser_hr_employee_id'),
    ]

    operations = [
        # Tidak ada pemulihan: bawaan baru dibuat otomatis, salinan lama tidak berisi pilihan pengguna.
        migrations.RunPython(hapus_salinan_bawaan_lama, migrations.RunPython.noop),
    ]
