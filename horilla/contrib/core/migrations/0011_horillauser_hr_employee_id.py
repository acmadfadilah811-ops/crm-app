# Generated manually (trimmed from Django's autodetected output, which also
# bundled 4 unrelated AlterField timezone-choices drift ops on
# BusinessHour/Company/HorillaUser/ShiftHour -- pre-existing metadata drift
# unrelated to this change, left untouched here per single-concern rule).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_alter_recyclebin_deleted_by_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='horillauser',
            name='hr_employee_id',
            field=models.IntegerField(blank=True, null=True, unique=True),
        ),
    ]
