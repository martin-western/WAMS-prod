# -*- coding: utf-8 -*-
# Generated by Django 1.11.26 on 2020-10-21 11:09
from __future__ import unicode_literals

from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('WAMSApp', '0005_auto_20201021_1639'),
        ('auth', '0008_alter_user_username_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesAppUser',
            fields=[
                ('user_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('customer_id', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('fcm_id_list', models.TextField(default='{}')),
                ('contact_number', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('country', models.CharField(blank=True, default='', max_length=200, null=True)),
                ('favourite_products', models.ManyToManyField(blank=True, to='WAMSApp.Product')),
            ],
            options={
                'verbose_name': 'SalesAppUser',
                'verbose_name_plural': 'SalesAppUsers',
            },
            bases=('auth.user',),
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
    ]
