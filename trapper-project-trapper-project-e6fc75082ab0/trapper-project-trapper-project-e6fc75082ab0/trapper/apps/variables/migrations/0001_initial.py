# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-07 13:45
from __future__ import unicode_literals

from django.db import migrations, models
import trapper.apps.variables.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Variable',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('namespace', models.CharField(max_length=127, verbose_name='Namespace')),
                ('name', models.CharField(max_length=127, verbose_name='Name')),
                ('value', trapper.apps.variables.fields.ObjectField(verbose_name='Value')),
            ],
            options={
                'ordering': ('namespace', 'name'),
                'verbose_name': 'Variable',
                'verbose_name_plural': 'Variables',
            },
        ),
        migrations.AlterUniqueTogether(
            name='variable',
            unique_together=set([('namespace', 'name')]),
        ),
    ]
