# -*- coding: utf-8 -*-
"""Forms used by storage application.

This module contains forms used by :class:`apps.storage.models.Resource` and
:class:`apps.storage.models.Collection` models
"""
from __future__ import unicode_literals

import os
import zipfile
import shutil

from django import forms
from django.forms.widgets import DateTimeInput
from django.db.models import Q
from django.forms.widgets import Textarea
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.safestring import mark_safe
from django.template.defaultfilters import filesizeformat

from crispy_forms.layout import Layout, Fieldset
from taggit.forms import TagField

from trapper.middleware import get_current_user
from trapper.apps.common.forms import (
    BaseCrispyModelForm, BaseCrispyForm, BaseBulkUpdateForm
)
from trapper.apps.common.widgets import DisabledTextInput
from trapper.apps.common.fields import (
    OwnerModelMultipleChoiceField, SimpleTagField, RestrictedFileField
)
from trapper.apps.common.tools import parse_pks
from trapper.apps.common.utils.identity import create_hashcode
from trapper.apps.storage.models import Resource, Collection
from trapper.apps.storage.collection_upload import CollectionProcessor
from trapper.apps.storage.taxonomy import ResourceMimeType, CollectionSettings
from trapper.apps.research.models import ResearchProject
from trapper.apps.research.taxonomy import ResearchProjectRoleType
from trapper.apps.geomap.models import Deployment
from trapper.apps.accounts.utils import (
    get_external_collections_path, get_external_resources_path
)

User = get_user_model()


class ResourceForm(BaseCrispyModelForm):
    """
    Modelform for creating :class:`apps.storage.models.Resource` objects
    """
    file = RestrictedFileField(
        help_text='File size must be under {max}'.format(
            max=filesizeformat(settings.MAX_UPLOAD_SIZE)
        )
    )
    extra_file = RestrictedFileField(
        help_text='File size must be under {max}'.format(
            max=filesizeformat(settings.MAX_UPLOAD_SIZE)
        )
    )
    date_recorded = forms.DateTimeField(
        input_formats=settings.DATETIME_INPUT_FORMATS,
        widget=DateTimeInput(format='%d.%m.%Y %H:%M:%S')
    )
    managers = OwnerModelMultipleChoiceField(
        queryset=User.objects.all(), required=False
    )
    tags = TagField(required=False)

    select2_fields = (
        'deployment', ''
    )

    class Meta:
        model = Resource
        exclude = [
            'owner', 'date_uploaded'
        ]

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'name',
                'description',
                'date_recorded',
                'deployment',
                'file',
                'preselected_file',
                'extra_file',
                'preselected_extra_file',
                'tags',
                'status',
                'managers',
                'inherit_prefix',
            ),
        )

    def save(self, force_insert=False, force_update=False, commit=True):
        """On resource save, the update of the metadata is performed
        (see :meth:`.Resource.update_metadata`)
        """
        resource = super(ResourceForm, self).save(commit=False)

        if 'file' in self.fields or 'preselected_file' in self.fields:
            if not resource.file:
                preselected_file = self.cleaned_data['preselected_file']
                name, ext = os.path.splitext(
                    os.path.basename(preselected_file)
                )
                media_path = '{upload_dir}{name}_{hash}{ext}'.format(
                    upload_dir=Resource.UPLOAD_DIR,
                    name=name,
                    ext=ext,
                    hash=create_hashcode()
                )
                shutil.move(
                    preselected_file,
                    os.path.join(settings.MEDIA_ROOT, media_path)
                )
                resource.file = media_path

        if (
            'extra_file' in self.fields or
            'preselected_extra_file' in self.fields
        ):
            preselected_extra_file = self.cleaned_data['preselected_extra_file']
            if not resource.extra_file and preselected_extra_file:
                name, ext = os.path.splitext(
                    os.path.basename(preselected_extra_file)
                )
                media_path = '{upload_dir}{name}_{hash}{ext}'.format(
                    upload_dir=Resource.UPLOAD_DIR,
                    name=name,
                    ext=ext,
                    hash=create_hashcode()
                )
                shutil.move(
                    preselected_extra_file,
                    os.path.join(settings.MEDIA_ROOT, media_path)
                )
                resource.extra_file = media_path

        resource.save()
        resource.update_metadata()
        resource.generate_thumbnails()

        resource.managers = self.cleaned_data['managers']
        return resource

    def __init__(self, *args, **kwargs):
        """Customize each instance of form by setting queryset for
        locations and tags if fields are available in form.

        Also add workflow for selecting uploaded resources using alternative
        methods:

        * either file or preselected resource file is required (but not both)
        * if extra file is uploaded, it cannot be preselected
        * preselected resource file and extra file cannot be the same
        """
        super(ResourceForm, self).__init__(*args, **kwargs)

        if 'file' in self.fields:
            self.fields['file'].required = False

        if 'extra_file' in self.fields:
            self.fields['extra_file'].required = False

        for fieldname in ['managers']:
            self.fields[fieldname].help_text = None

        if 'deployment' in self.fields:
            self.fields[
                'deployment'
            ].queryset = Deployment.objects.get_accessible(
                editable_only = True
            )

        if 'tags' in self.fields:
            tags = ",".join(Resource.tags.values_list('name', flat=True))
            self.fields['tags'].widget.attrs['data-tags'] = tags

        if 'file' in self.fields or 'extra_file' in self.fields:
            user = get_current_user()
            self.username = user.username
            path = get_external_resources_path(username=self.username)
            files = []

            if not os.path.exists(path):
                os.makedirs(path)

            for filename in os.listdir(path):
                ext = os.path.splitext(filename)[1]
                if ext in ResourceMimeType.MEDIA_EXTENSIONS:
                    files.append(filename)
            files.sort()

        if 'file' in self.fields:
            self.fields['preselected_file'] = forms.ChoiceField(
                label="Uploaded file",
                choices=[('', '---------')] + zip(files, files),
                required=False,
                help_text='Optionally choose already uploaded file (e.g. through FTP)'
            )
        if 'extra_file' in self.fields:
            self.fields['preselected_extra_file'] = forms.ChoiceField(
                label="Uploaded extra file",
                choices=[('', '---------')] + zip(files, files),
                required=False,
                help_text='Optionally choose already uploaded extra file (e.g. through FTP)'
            )

    def clean(self):
        """
        * file and preselected uploaded file cannot be filled at the same time
        * extra file and preselected uploaded extra file cannot be filled at
            the same time
        * the same file cannot be preselected as file and extra file at the
            same time
        """
        cleaned_data = self.cleaned_data
        preselected_file = None
        preselected_extra_file = None
        file_fields_error_msg = (
            'Either a new file or already uploaded one is required. '
            'But you can not fill in both fields.'
        )
        # Validation for file and preselected file
        if 'file' in self.fields or 'preselected_file' in self.fields:
            uploaded_file = cleaned_data.get('file')
            preselected_file = cleaned_data.get('preselected_file')

            if not uploaded_file and not preselected_file:
                errors = mark_safe(file_fields_error_msg)
                raise forms.ValidationError(errors)

            if uploaded_file and preselected_file:
                errors = mark_safe(file_fields_error_msg)
                raise forms.ValidationError(errors)

        # Validate for extra file and preselected extra file
        if (
            'extra_file' in self.fields or
            'preselected_extra_file' in self.fields
        ):
            uploaded_extra_file = cleaned_data.get('extra_file')
            preselected_extra_file = cleaned_data.get('preselected_extra_file')

            if uploaded_extra_file and preselected_extra_file:
                errors = mark_safe(file_fields_error_msg)
                raise forms.ValidationError(errors)

        # Validation for preselected file and preselected extra file - they
        # cannot be the same file
        if (
            preselected_file and preselected_extra_file and
            preselected_file == preselected_extra_file
        ):
            errors = mark_safe(
                'File and extra file can not be the same files.'
            )
            raise forms.ValidationError(errors)
        return cleaned_data

    def clean_preselected_file(self):
        """Preselected file has to exist on server.
        If it does, then full path is returned as resource_file"""
        preselected_file = self.cleaned_data.get('preselected_file')
        file_path = None
        if preselected_file:
            file_path = get_external_resources_path(
                username=self.username, filename=preselected_file
            )
            if not os.path.exists(file_path):
                errors = mark_safe(
                    'Selected resource file does not exist on server anymore.'
                )
                raise forms.ValidationError(errors)
        return file_path

    def clean_preselected_extra_file(self):
        """Preselected extra file has to exist on server.
        If it does, then full path is returned as resource_extra_file"""
        preselected_extra_file = self.cleaned_data.get('preselected_extra_file')
        file_path = None
        if preselected_extra_file:
            file_path = get_external_resources_path(
                username=self.username, filename=preselected_extra_file
            )
            if not os.path.exists(file_path):
                errors = mark_safe(
                    'Selected resource extra file does not exist on '
                    'server anymore.'
                )
                raise forms.ValidationError(errors)
        return file_path


class SimpleResourceForm(ResourceForm):
    """
    """

    class Meta:
        model = Resource
        exclude = [
            'owner', 'mime_type', 'extra_mime_type',
            'resource_type', 'file', 'extra_file', 'inherit_prefix',
            'custom_prefix'
        ]

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'name',
                'date_recorded',
                'deployment',
                'tags',
                'status',
                'managers',
            ),
        )

    def clean(self):
        return super(ResourceForm, self).clean()


class BulkUpdateResourceForm(BaseBulkUpdateForm):
    """
    """

    tags2add = SimpleTagField(
        required=False, label='Tags to add'
    )
    tags2remove = SimpleTagField(
        required=False, label='Tags to remove'
    )

    select2_fields = ('deployment',)

    class Meta:
        model = Resource
        fields = (
            'status', 
            'deployment', 
            'managers'
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'status',
                'deployment',
                'tags2add',
                'tags2remove',
                'managers',
                'records_pks'
            ),
        )

    def __init__(self, *args, **kwargs):
        super(BulkUpdateResourceForm, self).__init__(*args, **kwargs)
        tags = ",".join(Resource.tags.values_list('name', flat=True))
        self.fields['tags2add'].widget.attrs['data-tags'] = tags
        self.fields['tags2add'].help_text = ''
        self.fields['tags2remove'].widget.attrs['data-tags'] = tags
        self.fields['tags2remove'].help_text = ''
        self.fields['managers'].help_text = ''


class ResourceDataPackageForm(BaseCrispyForm):
    """
    """

    package_name = forms.CharField(
        required=False, max_length=200,
        help_text='Name of your data package. If not provided it will be set automatically.'
    )

    metadata = forms.BooleanField(
        initial=False, required=False,
        label='Attach basic metadata',
        help_text='If checked, a data package will contain a table with basic metadata.'
    )

    resources_pks = forms.CharField(
        widget=forms.HiddenInput(),
    )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'package_name',
                'metadata',
                'resources_pks'
            ),
        )

    def clean_resources_pks(self):
        resources_pks = self.cleaned_data.pop('resources_pks', None)
        if resources_pks:
            pks_list = parse_pks(resources_pks)
            resources = Resource.objects.get_accessible().filter(
                pk__in=pks_list
            )
            if resources:
                self.cleaned_data['resources'] = resources


class CollectionForm(BaseCrispyModelForm):
    """Form definition for creating :class:apps.storage.models.Collection`
    objects"""

    managers = OwnerModelMultipleChoiceField(
        queryset=User.objects.all(), required=False
    )
    resources_pks = forms.CharField(
        widget=forms.widgets.HiddenInput, required=False
    )
    app = forms.CharField(
        widget=forms.widgets.HiddenInput, required=False
    )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'name',
                'description',
                'managers',
                'status',
                'resources_pks',
                'app'
            ),
        )

    class Meta:
        model = Collection
        exclude = ['owner', 'members', 'resources']

    def __init__(self, *args, **kwargs):
        super(CollectionForm, self).__init__(*args, **kwargs)
        self.fields['managers'].help_text = None
    
    def clean(self):
        """
        When collection and its resources are saved and the status 
        of this collection is set to "Public" or "OnDemand" check
        if this collection can be published or shared. This should 
        be only possible when a user has editing rights to all 
        resources that are part of this collection.
        """
        cleaned_data = super(CollectionForm, self).clean()
        status = cleaned_data.get('status')

        resources_pks = cleaned_data.pop('resources_pks', None)
        app = cleaned_data.pop('app', None)
        
        if resources_pks:
            pks_list = parse_pks(resources_pks)
            if app == 'media_classification':
                resources = Resource.objects.get_accessible().filter(
                    classifications__pk__in=pks_list
                )
            else:
                resources = Resource.objects.get_accessible().filter(
                    pk__in=pks_list
                )
            if resources:
                cleaned_data['resources'] = resources                

        if status != 'Private':
            if self.instance.pk:
                resources = self.instance.resources.all()
            else:
                resources = cleaned_data.get('resources', None)
            if not resources:
                return cleaned_data
            user = get_current_user()
            n = resources.exclude(
                Q(owner=user) | Q(managers=user)
            ).count()
            if n != 0:
                errors = mark_safe(
                    'You are not allowed to set the status of this collection '
                    'to <strong>{status}</strong> as you are not the owner of all resources '
                    'that are part of this collection.'.format(
                        status=status
                    )
                )
                raise forms.ValidationError(errors)
        return cleaned_data

    def save(self, force_insert=False, force_update=False, commit=True):
        """When form is saved, then all m2m relations are processed:

        * resources that can be added to collection are saved
        * managers are updated
        """

        collection = super(CollectionForm, self).save(commit=False)
        resources = self.cleaned_data.get('resources', None)
        managers = self.cleaned_data.get('managers', None)
        if commit:
            collection.save()
        if resources:
            collection.resources = resources
        if managers:
            collection.managers = managers
        return collection


class BulkUpdateCollectionForm(BaseBulkUpdateForm):
    """
    """

    class Meta:
        model = Collection
        fields = (
            'status', 'managers'
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'status',
                'managers',
                'records_pks'
            ),
        )

    def __init__(self, *args, **kwargs):
        super(BulkUpdateCollectionForm, self).__init__(*args, **kwargs)
        self.fields['managers'].help_text = ''


class CollectionRequestForm(BaseCrispyForm):
    """
    """

    REQUIRED_PROJECT_ROLES = [
        ResearchProjectRoleType.ADMIN,
        ResearchProjectRoleType.EXPERT
    ]

    project = forms.ModelChoiceField(
        queryset=ResearchProject.objects.none(),
        help_text='In which project are you planning to use the requested collection?'
    )
    text = forms.CharField(widget=Textarea())
    object_pk = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, **kwargs):
        """Limit available research projects only to those that are
        accessible to a user"""
        super(CollectionRequestForm, self).__init__(**kwargs)
        user = get_current_user()
        self.fields['project'].queryset = ResearchProject.objects.filter(
            status=True
        ).filter(
            Q(owner=user) |
            (
                Q(project_roles__name__in=self.REQUIRED_PROJECT_ROLES) &
                Q(project_roles__user=user)
            )
        ).distinct()

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'project',
                'text',
                'object_pk'
            ),
        )


class CollectionUploadConfigForm(BaseCrispyForm):
    """
    """
    definition_file = forms.FileField(label='Data package definition file (YAML)')

    def clean_definition_file(self):
        """Validate config file to be valid yaml file and
        match schema used for uploading collections"""
        user = get_current_user()
        definition_file = self.cleaned_data['definition_file'].file.read()

        processor = CollectionProcessor(
            definition_file=definition_file,
            owner=user
        )

        errors = processor.validate_definition()
        if errors:
            errors = mark_safe(
                errors.replace(CollectionProcessor.SEPARATOR, '<br/>')
            )
            raise forms.ValidationError(errors)
        return definition_file

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'definition_file'
            ),
        )


class CollectionUploadDataForm(BaseCrispyForm):
    """
    """
    archive_file = RestrictedFileField(
        label='Collection archive', required=False,
        max_upload_size=settings.MAX_UPLOAD_COLLECTION_SIZE,
        help_text='File size must be under {max}. Only ZIP files are allowed.'.format(
            max=filesizeformat(settings.MAX_UPLOAD_COLLECTION_SIZE)
        )
    )

    def __init__(self, *args, **kwargs):
        """Get currently logged in user that will be used to determine
        where to look for previously uploaded files, and then
        generate list of files that are available for selection (by default
        only .zip files are allowed)"""
        super(CollectionUploadDataForm, self).__init__(*args, **kwargs)

        user = get_current_user()
        self.username = user.username
        path = get_external_collections_path(username=self.username)
        files = []

        # If upload user directory doesn't exists, create it
        if not os.path.exists(path):
            os.makedirs(path)

        for filename in os.listdir(path):
            ext = os.path.splitext(filename)[1]
            if ext in CollectionSettings.MEDIA_EXTENSIONS:
                files.append(filename)
        files.sort()

        self.fields['uploaded_media'] = forms.ChoiceField(
            label="Uploaded archive",
            choices=[('', '---------')] + zip(files, files),
            required=False,
            help_text='Optionally choose already uploaded data package (e.g. through FTP)'
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'archive_file',
                'uploaded_media'
            ),
        )

    def clean(self):
        """Verify that either archive file was submitted or already uploaded
        file was selected"""
        cleaned_data = self.cleaned_data

        archive_file = cleaned_data.get('archive_file')
        uploaded_media = cleaned_data.get('uploaded_media')

        if not archive_file and not uploaded_media:
            errors = mark_safe(
                'You have to choose one of two options.'
            )
            raise forms.ValidationError(errors)

        elif archive_file and uploaded_media:
            errors = mark_safe(
                'You can select only one option.'
            )
            raise forms.ValidationError(errors)
        return cleaned_data

    def clean_archive_file(self):
        """Uploaded archive has to be at least valid zipfile"""
        archive_file = self.cleaned_data.get('archive_file')
        if archive_file and not zipfile.is_zipfile(archive_file):
            errors = mark_safe(
                'This is not a valid ZIP file.'
            )
            raise forms.ValidationError(errors)
        return archive_file

    def clean_uploaded_media(self):
        """Uploaded media has to exist on the server.
        If it does, then the full path is returned as uploaded_media"""
        uploaded_media = self.cleaned_data.get('uploaded_media')
        file_path = None
        if uploaded_media:
            file_path = get_external_collections_path(
                username=self.username, filename=uploaded_media
            )
            if not os.path.exists(file_path):
                errors = mark_safe(
                    'We are sorry but this data package does not exist on '
                    'the server anymore.'
                )
                raise forms.ValidationError(errors)
        return file_path
