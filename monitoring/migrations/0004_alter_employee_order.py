# Generated by Django 4.2.5 on 2024-06-21 04:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0011_remove_equipment_sold_equipment_quantity'),
        ('monitoring', '0003_jobtitle_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employee',
            name='order',
            field=models.ManyToManyField(blank=True, related_name='workers', to='marketplace.order', verbose_name='order'),
        ),
    ]
