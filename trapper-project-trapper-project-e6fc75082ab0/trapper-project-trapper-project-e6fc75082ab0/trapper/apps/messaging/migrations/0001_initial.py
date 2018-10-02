# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-07 13:56
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import trapper.apps.common.fields
import trapper.apps.common.utils.identity


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('research', '0001_initial'),
        ('storage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CollectionRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('added_at', models.DateTimeField(auto_now_add=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('is_approved', models.NullBooleanField(choices=[(True, 'Approved'), (False, 'Declined'), (None, 'Not processed yet')], default=None)),
                ('collections', models.ManyToManyField(blank=True, related_name='collection_request', to='storage.Collection')),
            ],
            options={
                'ordering': ('-added_at', '-resolved_at'),
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hashcode', models.CharField(default=trapper.apps.common.utils.identity.create_hashcode, editable=False, help_text='Unique hash used to get message', max_length=64, verbose_name='Hashcode')),
                ('subject', models.CharField(max_length=255, verbose_name='Message subject')),
                ('text', trapper.apps.common.fields.SafeTextField(max_length=1000, verbose_name='Message body')),
                ('date_sent', models.DateTimeField(auto_now_add=True)),
                ('date_received', models.DateTimeField(blank=True, null=True)),
                ('message_type', models.PositiveIntegerField(choices=[(1, 'Standard message'), (2, 'Resource request'), (3, 'Collection request'), (4, 'Resource deleted'), (5, 'Collection deleted'), (6, 'Research project created')], default=1)),
                ('user_from', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sent_messages', to=settings.AUTH_USER_MODEL)),
                ('user_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='received_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_sent'],
            },
        ),
        migrations.AddField(
            model_name='collectionrequest',
            name='message',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='messaging.Message'),
        ),
        migrations.AddField(
            model_name='collectionrequest',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='research.ResearchProject'),
        ),
        migrations.AddField(
            model_name='collectionrequest',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='collection_requests', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='collectionrequest',
            name='user_from',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='my_collection_requests', to=settings.AUTH_USER_MODEL),
        ),
    ]