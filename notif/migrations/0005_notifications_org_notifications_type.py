# Generated by Django 4.2.5 on 2024-06-25 10:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authorization', '0008_userprofile_device_token'),
        ('notif', '0004_rename_notif_notifications_alter_notifications_table'),
    ]

    operations = [
        migrations.AddField(
            model_name='notifications',
            name='org',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='org_notif', to='authorization.organization'),
        ),
        migrations.AddField(
            model_name='notifications',
            name='type',
            field=models.CharField(default='Order', max_length=50),
        ),
    ]
