# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-06-07 13:56
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django_hstore.fields
import trapper.apps.common.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('research', '0001_initial'),
        ('storage', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Classification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_created=True)),
                ('static_attrs', django_hstore.fields.DictionaryField(blank=True, null=True)),
                ('status', models.BooleanField(choices=[(True, b'Approved'), (False, b'Rejected')], default=False)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True)),
                ('approved_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classifications_approved', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('resource__date_recorded',),
            },
        ),
        migrations.CreateModel(
            name='ClassificationDynamicAttrs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attrs', django_hstore.fields.DictionaryField(blank=True, null=True)),
                ('classification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dynamic_attrs', to='media_classification.Classification')),
            ],
        ),
        migrations.CreateModel(
            name='ClassificationProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('status', models.IntegerField(choices=[(1, b'Ongoing'), (2, b'Finished')], default=1)),
                ('deployment_based_nav', models.BooleanField(default=True, help_text=b'Enable deployment-based navigation', verbose_name=b'Deployment-based navigation')),
                ('enable_sequencing', models.BooleanField(default=True, help_text=b'Enable sequencing interface', verbose_name=b'Sequences')),
                ('enable_crowdsourcing', models.BooleanField(default=True, help_text='Status if crowd-sourcing enabled for the project')),
                ('disabled_at', models.DateTimeField(blank=True, editable=False, null=True)),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='ClassificationProjectCollection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_active', models.BooleanField(default=True, verbose_name=b'Active')),
                ('enable_sequencing_experts', models.BooleanField(default=True, help_text=b'Allow experts to create and edit sequences', verbose_name=b'Sequences editable by experts')),
                ('enable_crowdsourcing', models.BooleanField(default=True, help_text='Status if crowd-sourcing enabled for the project')),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='research.ResearchProjectCollection')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classification_project_collections', to='media_classification.ClassificationProject')),
            ],
        ),
        migrations.CreateModel(
            name='ClassificationProjectRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('name', models.IntegerField(choices=[(1, b'Admin'), (2, b'Expert'), (3, b'Collaborator')])),
                ('classification_project', models.ForeignKey(help_text='Project for which the role is defined', on_delete=django.db.models.deletion.CASCADE, related_name='classification_project_roles', to='media_classification.ClassificationProject')),
                ('user', models.ForeignKey(help_text='User for which the role is defined', on_delete=django.db.models.deletion.CASCADE, related_name='classification_project_roles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['user', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Classificator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('custom_attrs', django_hstore.fields.DictionaryField(blank=True, null=True)),
                ('predefined_attrs', django_hstore.fields.DictionaryField(blank=True, null=True)),
                ('dynamic_attrs_order', models.TextField(blank=True, null=True)),
                ('static_attrs_order', models.TextField(blank=True, null=True)),
                ('updated_date', models.DateTimeField(auto_now=True)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('description', trapper.apps.common.fields.SafeTextField(blank=True, max_length=2000, null=True)),
                ('disabled_at', models.DateTimeField(blank=True, editable=False, null=True)),
                ('template', models.CharField(choices=[(b'inline', b'Inline'), (b'tab', b'Tabbed')], default=b'inline', max_length=50)),
                ('copy_of', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='media_classification.Classificator')),
                ('disabled_by', models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_classificators', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ClassificatorHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('change_date', models.DateTimeField(auto_now_add=True)),
                ('classification_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classificator_history', to='media_classification.ClassificationProject')),
                ('classificator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classificator_history', to='media_classification.Classificator')),
            ],
        ),
        migrations.CreateModel(
            name='Sequence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence_id', models.IntegerField(blank=True, null=True)),
                ('description', models.TextField(blank=True, max_length=1000, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('collection', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sequences', to='media_classification.ClassificationProjectCollection')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['sequence_id'],
            },
        ),
        migrations.CreateModel(
            name='SequenceResourceM2M',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='storage.Resource')),
                ('sequence', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='media_classification.Sequence')),
            ],
        ),
        migrations.CreateModel(
            name='UserClassification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now_add=True)),
                ('static_attrs', django_hstore.fields.DictionaryField(blank=True, null=True)),
                ('classification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_classifications', to='media_classification.Classification')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_classifications', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='UserClassificationDynamicAttrs',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attrs', django_hstore.fields.DictionaryField()),
                ('userclassification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dynamic_attrs', to='media_classification.UserClassification')),
            ],
        ),
        migrations.AddField(
            model_name='sequence',
            name='resources',
            field=models.ManyToManyField(through='media_classification.SequenceResourceM2M', to='storage.Resource'),
        ),
        migrations.AddField(
            model_name='classificationproject',
            name='classificator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classification_projects', to='media_classification.Classificator'),
        ),
        migrations.AddField(
            model_name='classificationproject',
            name='collections',
            field=models.ManyToManyField(blank=True, related_name='classification_projects', through='media_classification.ClassificationProjectCollection', to='research.ResearchProjectCollection'),
        ),
        migrations.AddField(
            model_name='classificationproject',
            name='disabled_by',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='classificationproject',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='classificationproject',
            name='research_project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classification_projects', to='research.ResearchProject'),
        ),
        migrations.AddField(
            model_name='classification',
            name='approved_source',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='classification_approved', to='media_classification.UserClassification'),
        ),
        migrations.AddField(
            model_name='classification',
            name='collection',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classifications', to='media_classification.ClassificationProjectCollection'),
        ),
        migrations.AddField(
            model_name='classification',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classifications_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='classification',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classifications', to='media_classification.ClassificationProject'),
        ),
        migrations.AddField(
            model_name='classification',
            name='resource',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classifications', to='storage.Resource'),
        ),
        migrations.AddField(
            model_name='classification',
            name='sequence',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='classifications', to='media_classification.Sequence'),
        ),
        migrations.AddField(
            model_name='classification',
            name='updated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='classifications_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='classificationprojectrole',
            unique_together=set([('classification_project', 'user')]),
        ),
    ]
