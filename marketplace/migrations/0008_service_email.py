# Generated by Django 4.2.5 on 2024-05-20 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0007_size_equipment_currency_equipment_email_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='email',
            field=models.EmailField(blank=True, max_length=70),
        ),
    ]
