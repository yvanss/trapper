# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pandas

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from django.forms.widgets import DateTimeInput, HiddenInput
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.template.defaultfilters import filesizeformat

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, HTML

from leaflet_storage.models import Map
from timezone_field import TimeZoneFormField
from taggit.forms import TagField

from trapper.tools import gpxpy
from trapper.tools.gpxpy.gpx import GPXXMLSyntaxException

from trapper.middleware import get_current_user
from trapper.apps.common.forms import (
    BaseCrispyForm, BaseCrispyModelForm, BaseBulkUpdateForm
)
from trapper.apps.common.fields import (
    OwnerModelMultipleChoiceField, SimpleTagField, RestrictedFileField
)
from trapper.apps.common.tools import parse_pks
from trapper.apps.geomap.fields import LocationModelChoiceField
from trapper.apps.geomap.models import Location, Deployment
from trapper.apps.research.models import ResearchProject
from trapper.apps.research.taxonomy import ResearchProjectRoleType

User = get_user_model()


# Location forms

class LocationFilterForm(forms.ModelForm):
    search = forms.CharField(
        label='Search term', required=False,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'What are you looking for?',
                'onkeypress': 'return event.keyCode!=13'
            }
        ),
        help_text='You can search by locations & deployments metadata.'
    )
    research_project = forms.ModelChoiceField(
        queryset=None, required=False
    )
    locations_map = forms.CharField(
        widget=forms.HiddenInput(), required=False
    )
    in_bbox = forms.CharField(
        widget=forms.HiddenInput(), required=False
    )
    radius = forms.CharField(
        widget=forms.HiddenInput(), required=False,
    )

    class Meta:
        model = Location
        exclude = ['owner', 'is_public']

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_id = 'filter-locations-form'
        self.helper.error_text_inline = True
        self.helper.form_show_errors = False
        self.helper.help_text_inline = False
        self.helper.form_show_labels = True
        self.helper.layout = Layout(
            Fieldset(
                'Basic filters',
                'locations_map',
                'search',
                'research_project'
            ),
            Fieldset(
                'Spatial filters',
                'in_bbox',
                'radius'
            ),
        )
        super(LocationFilterForm, self).__init__(*args, **kwargs)
        user = get_current_user()
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            user = user,
            role_levels = ResearchProjectRoleType.EDIT
        )


class LocationImportForm(BaseCrispyForm):
    """Upload form for the locations file."""

    csv_file = RestrictedFileField(
        help_text='File size must be under {max}'.format(
            max=filesizeformat(settings.MAX_UPLOAD_SIZE)
        ),
        # add'force-download' as some browsers e.g. firefox???
        # set this content-type when uploading csv
        file_types=[
            'csv', 'txt', 'force-download',
            # csvs produced by excel
            'vnd.ms-excel'
        ], 
        required=False
    )
    gpx_file = RestrictedFileField(
        help_text='File size must be under {max}'.format(
            max=filesizeformat(settings.MAX_UPLOAD_SIZE)
        ), 
        file_types=[
            'gpx', 'xml', 'force-download', 'octet-stream'
        ], required=False
    )
    timezone = TimeZoneFormField(
        initial=timezone.get_current_timezone(),
        help_text='The chosen timezone will be set for all imported locations.'
    )
    research_project = forms.ModelChoiceField(queryset=None, required=False)

    select2_fields = (
        'timezone',
    )

    def __init__(self, *args, **kwargs):

        super(LocationImportForm, self).__init__(*args, **kwargs)

        user = get_current_user()
        self.fields['research_project'].help_text = None
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            user = user,
            role_levels = ResearchProjectRoleType.EDIT
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'csv_file',
                'gpx_file',
                'timezone',
                'research_project',
            ),
        )

    def process_gpx_file(self, gpx_file):
        if gpx_file:
            try:
                gpx = gpxpy.parse(gpx_file)
            except GPXXMLSyntaxException:
                raise forms.ValidationError(
                    'Invalid file format.', code='invalid'
                )
            else:
                self.cleaned_data['gpx_data'] = gpx

    def clean_gpx_file(self):
        """Validate gpx file that has been uploaded"""
        gpx_file = self.cleaned_data.get('gpx_file')
        self.process_gpx_file(gpx_file=gpx_file)
        return gpx_file

    def clean_csv_file(self):
        headers = [
            'location_id', 'X', 'Y'
        ]
        csv = self.cleaned_data.get('csv_file')
        if not csv:
            return None
        try:
            df = pandas.read_csv(csv, sep=',', dtype=object)
        except pandas.parser.CParserError:
            errors = mark_safe(
                'Can not parse file: {file}'.format(file=csv.name)
            )
            raise forms.ValidationError(errors)
        # check if csv file includes all obligatory columns
        intersection = set(headers).intersection(set(df.columns))
        if not len(intersection) == len(headers):
            errors = mark_safe(
                'Wrong structure of csv file. '
                'Check if your file includes the following headers: '
                '<strong>{headers}</strong>.'.format(
                    headers=headers,
                )
            )
            raise forms.ValidationError(errors)
        self.cleaned_data['df'] = df
        return csv

    def clean(self):
        """
        """
        cleaned_data = self.cleaned_data

        if not self.errors:
            csv_file = cleaned_data.get('csv_file')
            gpx_file = cleaned_data.get('gpx_file')

            # csv file and gpx file cannot be filled at the same time
            if not csv_file and not gpx_file:
                errors = mark_safe(
                    'You have to provide either csv file or gpx file.'
                )
                raise forms.ValidationError(errors)

            elif csv_file and gpx_file:
                errors = mark_safe(
                    'I am confused. Decide which file you want to upload.'
                )
                raise forms.ValidationError(errors)

        return cleaned_data



class CreateLocationForm(BaseCrispyModelForm):
    """Creating new location"""
    latitude = forms.FloatField(max_value=90.0, min_value=-90.0,
                                validators=[MaxValueValidator(90.0),
                                            MinValueValidator(-90.0)])
    longitude = forms.FloatField(max_value=180.0, min_value=-180.0,
                                 validators=[MaxValueValidator(180.0),
                                             MinValueValidator(-180.0)])

    class Meta:
        model = Location
        fields = ('location_id', 'coordinates', 'latitude', 'longitude', 'timezone', 'name', 'description',
                  'research_project')

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(CreateLocationForm, self).__init__(*args, **kwargs)
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            role_levels=ResearchProjectRoleType.EDIT
        )
        self.fields['coordinates'].widget = HiddenInput()
        instance = kwargs.get('instance')
        if instance is not None:
            self.fields['latitude'].initial = instance.coordinates.get_y()
            self.fields['longitude'].initial = instance.coordinates.get_x()
        else:
            self.fields['timezone'].initial = timezone.get_current_timezone()

    def clean(self):
        cleaned_data = super(CreateLocationForm, self).clean()
        rp = cleaned_data.get('research_project')
        lid = cleaned_data.get('location_id')
        if self.instance.pk is None:
            if rp and lid and Location.objects.filter(
                    research_project=rp, location_id=lid
            ).exists():
                raise forms.ValidationError('Location with this id already exists.')
        return cleaned_data


class UpdateMapPermissionsForm(forms.ModelForm):
    """ Change permissions form with select2 widget
    for changing permissions on maps"""

    def __init__(self, *args, **kwargs):
        owner = kwargs.pop('owner', None)
        super(UpdateMapPermissionsForm, self).__init__(*args, **kwargs)
        self.fields['editors'].help_text = None
        self.fields['editors'].queryset = User.objects.exclude(
            pk=owner.pk)

    class Meta:
        model = Map
        fields = ('edit_status', 'editors', 'share_status')


class BulkUpdateLocationForm(BaseBulkUpdateForm):
    """
    """

    research_project = forms.ModelChoiceField(
        queryset=None, required=False
    )
    is_public = forms.ChoiceField(
        choices=[(False, 'False'), (True, 'True')],
        widget=forms.Select()
    )

    select2_fields = ('timezone',)

    class Meta:
        model = Location
        fields = (
            'research_project', 'timezone', 'is_public',
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'research_project',
                'timezone',
                'is_public',
                'records_pks'
            ),
        )

    def __init__(self, *args, **kwargs):
        super(BulkUpdateLocationForm, self).__init__(*args, **kwargs)
        self.fields['research_project'].help_text = None
        self.fields['timezone'].help_text = None
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            role_levels = ResearchProjectRoleType.EDIT
        )


# Deployment forms


class DeploymentForm(BaseCrispyModelForm):
    """
    Modelform for creating :class:`apps.geomap.models.Deployment` objects
    """
    start_date = forms.DateTimeField(
        input_formats=settings.DATETIME_INPUT_FORMATS,
        widget=DateTimeInput(format='%d.%m.%Y %H:%M:%S')
    )
    end_date = forms.DateTimeField(
        input_formats=settings.DATETIME_INPUT_FORMATS,
        widget=DateTimeInput(format='%d.%m.%Y %H:%M:%S')
    )
    managers = OwnerModelMultipleChoiceField(
        queryset=User.objects.all(), required=False
    )
    location = LocationModelChoiceField(queryset=None)
    tags = TagField(required=False)

    select2_fields = (
        'location',
    )

    class Meta:
        model = Deployment
        exclude = [
            'owner'
        ]

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'deployment_code',
                'location',
                HTML(
                    '{% include "geomap/deployment_form_map.html" %}'
                ),
                'research_project',
                'start_date',
                'end_date',
                'correct_setup',
                'correct_tstamp',
                'view_quality',
                'tags',
                'comments',
                'managers',
            ),
        )

    def save(self, force_insert=False, force_update=False, commit=True):
        deployment = super(DeploymentForm, self).save(commit=False)
        deployment.save()
        deployment.managers = self.cleaned_data['managers']
        return deployment

    def __init__(self, *args, **kwargs):
        """Customize each instance of a form by setting a queryset for
        a location if it is available in a form.
        """
        super(DeploymentForm, self).__init__(*args, **kwargs)

        for fieldname in ['research_project', 'managers']:
            self.fields[fieldname].help_text = None

        if 'location' in self.fields:
            self.fields['location'].queryset = Location.objects.get_available(
                editable_only=True
            )

        if 'research_project' in self.fields:
            self.fields[
                'research_project'
            ].queryset = ResearchProject.objects.get_accessible(
                role_levels=ResearchProjectRoleType.EDIT
            )

        if 'tags' in self.fields:
            tags = ",".join(Deployment.tags.values_list('name', flat=True))
            self.fields['tags'].widget.attrs['data-tags'] = tags


class SimpleDeploymentForm(DeploymentForm):
    """Simple version of :class:`DeploymentForm` that is used for
    dynamic edit form"""

    class Meta:
        model = Deployment
        exclude = [
            'owner', 'location', 'comments', ''
        ]

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'deployment_code',
                'research_project',
                'start_date',
                'end_date',
                'correct_setup',
                'correct_tstamp',
                'view_quality',
                'tags',
                'managers',
            ),
        )


class BulkUpdateDeploymentForm(BaseBulkUpdateForm):
    """
    """

    tags2add = SimpleTagField(
        required=False, label='Tags to add'
    )
    tags2remove = SimpleTagField(
        required=False, label='Tags to remove'
    )
    research_project = forms.ModelChoiceField(
        queryset=None, required=False
    )

    class Meta:
        model = Deployment
        fields = (
            'deployment_code', 'research_project',
            'start_date', 'end_date',
            'view_quality', 'managers'
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'deployment_code',
                'research_project',
                'start_date',
                'end_date',
                'view_quality',
                'tags2add',
                'tags2remove',
                'managers',
                'records_pks'
            ),
        )

    def __init__(self, *args, **kwargs):
        super(BulkUpdateDeploymentForm, self).__init__(*args, **kwargs)
        tags = ",".join(Deployment.tags.values_list('name', flat=True))
        self.fields['tags2add'].widget.attrs['data-tags'] = tags
        self.fields['tags2add'].help_text = ''
        self.fields['tags2remove'].widget.attrs['data-tags'] = tags
        self.fields['tags2remove'].help_text = ''
        self.fields['managers'].help_text = ''
        self.fields['research_project'].help_text = None
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            role_levels = ResearchProjectRoleType.EDIT
        )


class BulkCreateDeploymentForm(DeploymentForm):
    """
    """
    locations_pks = forms.CharField(
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Deployment
        exclude = [
            'owner', 'location'
        ]

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'deployment_code',
                'research_project',
                'start_date',
                'end_date',
                'managers',
                'locations_pks'
            ),
        )

    def __init__(self, *args, **kwargs):
        super(BulkCreateDeploymentForm, self).__init__(*args, **kwargs)
        if 'research_project' in self.fields:
            self.fields[
                'research_project'
            ].queryset = ResearchProject.objects.get_accessible(
                role_levels=ResearchProjectRoleType.EDIT
            )
        self.fields['managers'].help_text = None
        self.fields['location'].required = False

    def clean_locations_pks(self):
        locations_pks = self.cleaned_data.pop('locations_pks', None)
        if locations_pks:
            pks_list = parse_pks(locations_pks)
            locations = Location.objects.get_available(
                editable_only=True
            ).filter(
                pk__in=pks_list
            )
            if locations:
                self.cleaned_data['locations'] = locations


class DeploymentImportForm(BaseCrispyForm):
    """
    """

    csv = RestrictedFileField(
        label='Deployments table (csv)',
        help_text='File size must be under {max}'.format(
            max=filesizeformat(settings.MAX_UPLOAD_SIZE)
        ),
        # add'force-download' as some browsers e.g. firefox???
        # set this content-type when uploading csv
        file_types=['csv', 'txt', 'force-download'], required=True
    )
    research_project = forms.ModelChoiceField(queryset=None)
    timezone = TimeZoneFormField(
        initial=timezone.get_current_timezone(),
        help_text='Provide a timezone to correctly process deployments "start" '
        'and "end" timestamps.'
    )

    select2_fields = (
        'timezone',
    )

    def __init__(self, *args, **kwargs):
        """"""

        super(DeploymentImportForm, self).__init__(*args, **kwargs)
        user = get_current_user()
        self.fields[
            'research_project'
        ].queryset = ResearchProject.objects.get_accessible(
            user = user,
            role_levels = ResearchProjectRoleType.EDIT
        )

    def get_layout(self):
        """
        """
        return Layout(
            Fieldset(
                '',
                'csv',
                'research_project',
                'timezone'
            ),
        )

    def clean(self):
        """
        """
        cleaned_data = self.cleaned_data

        if not self.errors:

            headers = [
                'deployment_id', 'deployment_code',
                'deployment_start', 'deployment_end',
                'location_id', 'correct_setup', 'correct_tstamp'
            ]

            csv = cleaned_data.get('csv')
            try:
                df = pandas.read_csv(csv, sep=',', dtype=object)
            except pandas.parser.CParserError:
                errors = mark_safe(
                    'Can not parse file: {file}'.format(file=csv.name)
                )
                raise forms.ValidationError(errors)

            intersection = set(headers).intersection(set(df.columns))
            if not len(intersection) == len(headers):
                errors = mark_safe(
                    'Wrong structure of csv file. '
                    'Check if your file includes the following headers: '
                    '<strong>{headers}</strong>.'.format(
                        headers=headers,
                    )
                )
                raise forms.ValidationError(errors)

            cleaned_data['df'] = df

        return cleaned_data
