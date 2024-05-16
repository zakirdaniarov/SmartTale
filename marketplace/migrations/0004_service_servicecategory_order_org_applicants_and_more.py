# Generated by Django 4.2.5 on 2024-05-14 21:15

import autoslug.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authorization', '0005_remove_userprofile_current_org_and_more'),
        ('marketplace', '0003_alter_equipment_category_alter_equipment_liked_by_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=70)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(max_length=1000, null=True)),
                ('size', models.CharField(max_length=100)),
                ('phone_number', models.CharField(max_length=20)),
                ('hide', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author_org', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_ads', to='authorization.organization')),
            ],
        ),
        migrations.CreateModel(
            name='ServiceCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='org_applicants',
            field=models.ManyToManyField(blank=True, related_name='applied_orders', to='authorization.organization'),
        ),
        migrations.AlterField(
            model_name='order',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_orders', to='authorization.userprofile'),
        ),
        migrations.CreateModel(
            name='ServiceImages',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('images', models.ImageField(blank=True, null=True, upload_to='Service images', verbose_name='Service images')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='marketplace.service')),
            ],
        ),
        migrations.AddField(
            model_name='service',
            name='category',
            field=models.ManyToManyField(blank=True, related_name='services', to='marketplace.servicecategory'),
        ),
        migrations.AddField(
            model_name='service',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_services', to='authorization.userprofile'),
        ),
    ]
