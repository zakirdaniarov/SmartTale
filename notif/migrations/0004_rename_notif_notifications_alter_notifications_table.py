# Generated by Django 4.2.5 on 2024-06-24 12:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('authorization', '0008_userprofile_device_token'),
        ('notif', '0003_alter_notif_table'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Notif',
            new_name='Notifications',
        ),
        migrations.AlterModelTable(
            name='notifications',
            table=None,
        ),
    ]
