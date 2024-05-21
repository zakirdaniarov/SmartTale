# Generated by Django 4.2.5 on 2024-05-20 05:05

import autoslug.fields
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('authorization', '0006_alter_organization_title'),
    ]

    operations = [
        migrations.CreateModel(
            name='Equipment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=70)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(choices=[('Som', 'Som'), ('Ruble', 'Ruble'), ('USD', 'USD'), ('Euro', 'Euro')], default='Som', max_length=10)),
                ('description', models.TextField(max_length=1000, null=True)),
                ('phone_number', models.CharField(max_length=20)),
                ('hide', models.BooleanField(default=False)),
                ('sold', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='equipment_ads', to='authorization.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='EquipmentCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(choices=[('Som', 'Som'), ('Ruble', 'Ruble'), ('USD', 'USD'), ('Euro', 'Euro')], default='Som', max_length=10)),
                ('description', models.TextField(max_length=1000, null=True)),
                ('deadline', models.DateField()),
                ('phone_number', models.CharField(max_length=20)),
                ('hide', models.BooleanField(default=False)),
                ('is_booked', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('Waiting', 'Waiting'), ('Process', 'Process'), ('Checking', 'Checking'), ('Sending', 'Sending'), ('Arrived', 'Arrived')], default='Waiting', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('booked_at', models.DateTimeField(blank=True, null=True)),
                ('is_finished', models.BooleanField(default=False)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('arrived_at', models.DateTimeField(blank=True, null=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_ads', to='authorization.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='OrderCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=60)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=70)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(choices=[('Som', 'Som'), ('Ruble', 'Ruble'), ('USD', 'USD'), ('Euro', 'Euro')], default='Som', max_length=10)),
                ('description', models.TextField(max_length=1000, null=True)),
                ('phone_number', models.CharField(max_length=20)),
                ('hide', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_ads', to='authorization.userprofile')),
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
        migrations.CreateModel(
            name='Size',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('size', models.CharField(max_length=10, unique=True)),
            ],
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
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='services', to='marketplace.servicecategory'),
        ),
        migrations.AddField(
            model_name='service',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_services', to='authorization.userprofile'),
        ),
        migrations.CreateModel(
            name='Reviews',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('review_text', models.TextField()),
                ('rating', models.IntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(5)])),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='order_reviews', to='marketplace.order')),
                ('reviewer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='authorization.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='OrderImages',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('images', models.ImageField(blank=True, null=True, upload_to='Order images', verbose_name='Order images')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='marketplace.order')),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='orders', to='marketplace.ordercategory'),
        ),
        migrations.AddField(
            model_name='order',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_orders', to='authorization.userprofile'),
        ),
        migrations.AddField(
            model_name='order',
            name='org_applicants',
            field=models.ManyToManyField(blank=True, related_name='applied_orders', to='authorization.organization'),
        ),
        migrations.AddField(
            model_name='order',
            name='org_work',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='received_orders', to='authorization.organization'),
        ),
        migrations.AddField(
            model_name='order',
            name='size',
            field=models.ManyToManyField(related_name='orders', to='marketplace.size'),
        ),
        migrations.CreateModel(
            name='EquipmentImages',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('images', models.ImageField(blank=True, null=True, upload_to='Equipment images', verbose_name='Equipment images')),
                ('equipment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='marketplace.equipment')),
            ],
        ),
        migrations.AddField(
            model_name='equipment',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='equipments', to='marketplace.equipmentcategory'),
        ),
        migrations.AddField(
            model_name='equipment',
            name='liked_by',
            field=models.ManyToManyField(blank=True, related_name='liked_equipment', to='authorization.userprofile'),
        ),
    ]
