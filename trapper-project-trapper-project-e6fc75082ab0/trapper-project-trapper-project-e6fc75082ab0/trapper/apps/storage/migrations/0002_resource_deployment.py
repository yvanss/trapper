# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-07 13:57
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geomap', '0001_initial'),
        ('storage', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='deployment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='resources', to='geomap.Deployment'),
        ),
    ]
