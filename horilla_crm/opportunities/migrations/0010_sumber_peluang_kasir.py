# Sumber Peluang baru "Kasir / Toko" untuk Peluang hasil order kasir ERP (2026-11-02). Hanya pilihan, tanpa
# perubahan skema database.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opportunities', '0009_verbose_name_erp'),
    ]

    operations = [
        migrations.AlterField(
            model_name='opportunity',
            name='lead_source',
            field=models.CharField(blank=True, choices=[('website', 'Website'), ('referral', 'Referral'), ('event', 'Event'), ('campaign', 'Campaign'), ('phone', 'Phone'), ('email', 'Email'), ('social media', 'Social Media'), ('partner', 'Partner'), ('kasir', 'Cashier / Store'), ('other', 'Other')], max_length=50, verbose_name='Lead Source'),
        ),
    ]
