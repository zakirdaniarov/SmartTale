# Generated by Django 4.2.5 on 2024-04-22 13:58

import authorization.models
import authorization.utils
import autoslug.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('email', authorization.utils.LowercaseEmailField(max_length=254, unique=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('is_verified', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=50)),
                ('last_name', models.CharField(max_length=50)),
                ('middle_name', models.CharField(max_length=50)),
                ('profile_image', models.ImageField(blank=True, max_length=500, null=True, upload_to='smarttale/user_profile')),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from=authorization.models.get_populate_from, unique_with=['first_name', 'last_name'])),
                ('gender', models.CharField(blank=True, choices=[('Male', 'Male'), ('Female', 'Female')], default=None, max_length=6, null=True)),
                ('birthday', models.DateField(default=None, null=True)),
                ('phone_number', models.CharField(blank=True, default=None, max_length=20, null=True)),
                ('subscription', models.DateTimeField(blank=True, default=None, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='user_profile', to=settings.AUTH_USER_MODEL, verbose_name='user')),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('slug', autoslug.fields.AutoSlugField(always_update=True, editable=False, populate_from='title', unique=True)),
                ('phone_number', models.CharField(blank=True, default=None, max_length=20, null=True)),
                ('subscription', models.DateTimeField(blank=True, default=None, null=True)),
                ('description', models.TextField()),
                ('active', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('founder', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='founder_organizations', to='authorization.userprofile', verbose_name='user')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='owner_organizations', to='authorization.userprofile', verbose_name='user')),
            ],
        ),
    ]
