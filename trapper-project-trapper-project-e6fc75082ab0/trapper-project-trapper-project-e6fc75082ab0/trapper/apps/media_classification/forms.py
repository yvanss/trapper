# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from collections import OrderedDict
from django.apps import apps
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model

import pandas
from extra_views import InlineFormSet
from crispy_forms.layout import Layout, HTML, Fieldset, Field
from trapper.apps.common.forms import ReadOnlyFieldsMixin
from trapper.apps.media_classification.models import (
    ClassificationProject, ClassificationProjectCollection,
    ClassificationProjectRole, Classificator, Sequence
)
from trapper.apps.media_classification.taxonomy import (
    ClassificatorSettings, ClassificationProjectRoleLevels
)
from trapper.apps.common.forms import (
    BaseCrispyModelForm, BaseCrispyForm, ProjectBaseInlineFormSet
)
from trapper.apps.common.tools import parse_pks
from trapper.apps.research.models import ResearchProject
from trapper.apps.research.taxonomy import ResearchProjectRoleType

from trapper.apps.storage.models import Resource
from trapper.middleware import get_current_user

User = get_user_model()


class ProjectRoleForm(BaseCrispyModelForm):
    """
    Model form for creating or updating
    :class:`apps.research.models.ResearchProjectRole` objects
    """
    form_style = 'inline'
    user = forms.ModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = ClassificationProjectRole
        exclude = ['classification_project', 'date_created']

    def __init__(self, *args, **kwargs):
        """Remove labels for formset"""
        super(ProjectRoleForm, self).__init__(*args, **kwargs)
        self.fields['user'].label = ''
        self.fields['user'].widget.attrs['class'] = 'select2-default'
        self.fields['name'].label = ''

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                Field('user', css_class='select2-default'),
                Field('name', css_class='select2-default'),
            ),
        )


class ProjectRoleInline(InlineFormSet):
    """Utility-class: ProjectRoles displayed as a InlineFormset"""
    model = ClassificationProjectRole
    form_class = ProjectRoleForm
    formset_class = ProjectBaseInlineFormSet
    extra = 1


class ProjectForm(BaseCrispyModelForm):
    """
    Form used for creating or updating
    :class:`apps.media_classification.models.ClassificationProject` objects
    """
    template_path = "media_classification/projects/"

    class Meta:
        model = ClassificationProject
        exclude = ['owner']

    def __init__(self, *args, **kwargs):
        """Preselect research project and check if user has access to given
        ResearchProject
        """
        super(ProjectForm, self).__init__(*args, **kwargs)
        user = get_current_user()

        projects_queryset = ResearchProject.objects.get_accessible(
            user=user,
            role_levels=ResearchProjectRoleType.EDIT
        )
        self.fields['research_project'].queryset = projects_queryset

        selected_value = self.initial.get('selected', None)
        if not self.instance.pk and selected_value:
            try:
                rproject = ResearchProject.objects.get(pk=selected_value)
            except ResearchProject.DoesNotExist:
                pass
            else:
                if rproject.can_update(user):
                    self.fields['research_project'].initial = rproject.pk
        classificator_field = self.fields.get('classificator', None)
        if classificator_field:
            classificator_field.queryset = classificator_field.queryset.filter(
                disabled_at__isnull=True
            )
        if not self.instance.pk:
            self.fields['status'].widget = forms.HiddenInput()

    def include(self, template_name):
        """Helper function used to inject django template into form
        Templates are used for position form fields or formsets inside form:

        * base form with sequencing, crowdsourcing, status as inline form
        * role formset
        """
        return HTML(
            '{{% include "{path}{name}" %}}'.format(
                path=self.template_path,
                name=template_name
            )
        )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'name',
                'research_project',
                'status',
                'classificator',
                self.include(template_name='form_inline.html'),
                self.include(template_name='role_formset.html'),
                ),
            )


class SequenceForm(BaseCrispyModelForm):
    """
    Form used for creating or updating
    :class:`apps.media_classification.models.Sequence` objects
    """

    resources = forms.CharField()

    class Meta:
        model = Sequence
        exclude = ['created', 'user', 'collection']
        widgets = {
            'resources': forms.HiddenInput()
        }

    def clean_resources(self):
        """Convert resources from string of comma separated integers
        into list of integers"""
        resources = self.data.get('resources', None)
        return parse_pks(pks=resources)

    def clean(self):
        """Verify that sequence contain at least one resource"""
        cd = super(SequenceForm, self).clean()
        resources = cd.get('resources')
        if not resources:
            raise forms.ValidationError("You did not select any resources.")
        return cd


class PredefinedAttributeForm(BaseCrispyForm):
    """Predefined attribute form has no staticly defined fields.
    ALl fields are generated dynamically"""

    select2_fields = (
        'selected_species',
    )

    def __init__(self, *args, **kwargs):
        """Based on predefined attribute definition, register proper fields
        in form.

        For generating form two settings from taxonomy
        :class:`apps.media_classification.taxonomy.` are used:

        * :class:`ClassificatorSettings.PREDEFINED_ATTRIBUTES_SIMPLE`
        * :class:`ClassificatorSettings.PREDEFINED_ATTRIBUTES_MODELS`
        """
        super(PredefinedAttributeForm, self).__init__(*args, **kwargs)

        attrs_simple = ClassificatorSettings.PREDEFINED_ATTRIBUTES_SIMPLE
        attrs_models = ClassificatorSettings.PREDEFINED_ATTRIBUTES_MODELS
        target_form_field = forms.ChoiceField(
            choices=ClassificatorSettings.TARGET_CHOICES,
            label='Target form',
            help_text='choose a target form for this attribute',
            required=False,
            initial='D',
        )
        required_form_field = forms.BooleanField(
            label='Required',
            required=False,
            initial=False,
        )
        self.layout = []
        # create form fields for simple predefined attributes
        for attr in attrs_simple:
            self.layout.append(HTML('<li class="panel-simple">'))
            target_attr = u'target_{name}'.format(name=attr)
            required_attr = u'required_{name}'.format(name=attr)
            self.fields[attr] = forms.BooleanField(
                required=False,
                label=attrs_simple[attr]['label'],
                help_text=attrs_simple[attr]['help_text'],
            )
            self.layout.append(attr)
            self.fields[target_attr] = target_form_field
            self.layout.append(target_attr)
            self.fields[required_attr] = required_form_field
            self.layout.append(required_attr)
            self.layout.append(HTML('</li>'))

        # create form fields for model-based predefined attributes
        for attr in attrs_models:
            selected_attr = u'selected_{name}'.format(name=attr)
            target_attr = u'target_{name}'.format(name=attr)
            required_attr = u'required_{name}'.format(name=attr)

            self.layout.append(HTML('<li class="panel-simple">'))
            model = apps.get_model(attrs_models[attr]['app'], attr)
            self.fields[attr] = forms.BooleanField(
                required=False,
                label=attrs_models[attr]['label']
            )
            self.layout.append(attr)

            self.fields[selected_attr] = forms.ModelMultipleChoiceField(
                queryset=model.objects,
                required=False,
                label='',
            )
            self.layout.append(selected_attr)
            self.fields[target_attr] = target_form_field
            self.layout.append(target_attr)
            self.fields[required_attr] = required_form_field
            self.layout.append(required_attr)
            self.layout.append(HTML('</li>'))

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(*self.layout)


class CustomAttributeForm(BaseCrispyForm):
    """Form description definition for custom attributes used for classifiator
    definition"""

    name = forms.CharField(label='Name', max_length=80, required=True)
    field_type = forms.ChoiceField(
        choices=ClassificatorSettings.FIELD_CHOICES,
        label='Type',
        required=True,
        initial='S'
    )
    target = forms.ChoiceField(
        choices=ClassificatorSettings.TARGET_CHOICES,
        label='Target form',
        help_text='choose a target form for this attribute',
        required=True,
        initial='D',
    )
    values = forms.CharField(
        label='Values',
        max_length=80,
        help_text=(
            'define possible values for this attribute (comma separated)'
        ),
        required=False,
    )
    initial = forms.CharField(
        label='Initial',
        max_length=80,
        help_text='define initial value',
        required=False,
    )
    required = forms.BooleanField(
        label='Required', required=False, initial=False,
    )
    description = forms.CharField(
        label='Description', required=True, widget=forms.Textarea()
    )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            'name',
            'field_type',
            'target',
            'values',
            'initial',
            'required',
            'description',
        )

    def clean(self):
        """Veirfy that all informations for dynamic attributes
        are correct:

        * name is required
        * attribute name cannot be used in predefined attributes
        * name cannot contain comma
        * boolean values don't use `values` field, the have
          predefined values: `True` or `False`
        * Given values have to be comma separated
        * If initial is given it has to be one of given values
        * Given values have to match defined type (i.e.
          integers have to be integers etc)

        """
        cleaned_data = super(CustomAttributeForm, self).clean()
        name = cleaned_data.get('name')
        field_type = cleaned_data.get('field_type')
        values = cleaned_data.get('values')
        initial = cleaned_data.get('initial')

        test_numeric_types = ClassificatorSettings.NUMERIC_MAPPERS

        if name and name in ClassificatorSettings.PREDEFINED_NAMES:
            self._errors['name'] = self.error_class(
                [u'Name is already used as predefined attribute']
            )
            del cleaned_data['name']
            return cleaned_data

        if name and ',' in name:
            self._errors['name'] = self.error_class(
                [u'Name cannot contain comma']
            )
            del cleaned_data['name']
            return cleaned_data

        if not name and (values or initial):
            self._errors['name'] = self.error_class(
                [u'You have forgotten about this field']
            )
            del cleaned_data['name']
            return cleaned_data

        if field_type == 'B' and values:
            self._errors['values'] = self.error_class(
                [u'Boolean type has two default possible values: "True" and '
                 u'"False". You do not need to specify anything here.']
            )
            del cleaned_data['values']
            return cleaned_data

        if values:
            # We make sure that it's unique list of values
            values_list = list(set(values.split(',')))

            if len(values_list) < 2:
                self._errors['values'] = self.error_class([
                    u'Parser error. Are these values really "comma-separated"?'
                ])
                del cleaned_data['values']
                return cleaned_data

            if initial and initial not in values_list:
                self._errors['initial'] = self.error_class([
                    u'Initial value must be one of defined possible values.'
                ])
                del cleaned_data['initial']

            if field_type in test_numeric_types:
                for value in values_list:
                    try:
                        test_numeric_types[field_type](value)
                    except ValueError as error:
                        self._errors['values'] = self.error_class(
                            [u'Value error: %s' % error]
                        )
                        del cleaned_data['values']
                        return cleaned_data

        else:
            if initial and field_type in test_numeric_types.keys():
                try:
                    test_numeric_types[field_type](initial)
                except ValueError as error:
                    self._errors['initial'] = self.error_class(
                        [u'Value error: %s' % error]
                    )
                    del cleaned_data['initial']
        return cleaned_data


class ClassificatorForm(BaseCrispyModelForm):
    """For used for classificator description"""

    class Meta:
        model = Classificator
        exclude = ['owner', 'custom_attrs', 'predefined_attrs']
        widgets = {
            'static_attrs_order': forms.HiddenInput(
                attrs={'id': 'id_static_attrs_order'}
            ),
            'dynamic_attrs_order': forms.HiddenInput(
                attrs={'id': 'id_dynamic_attrs_order'}
            ),
        }

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            'name',
            'template',
            'static_attrs_order',
            'dynamic_attrs_order',
        )


class ClassificationForm(ReadOnlyFieldsMixin, BaseCrispyForm):
    """Create classification forms (dynamic and static) dynamically based on
    an classificator object
    """

    def __init__(self, *args, **kwargs):
        fields_defs = kwargs.pop('fields_defs')
        attrs_order = kwargs.pop('attrs_order')
        readonly = kwargs.pop('readonly')
        self.base_fields = OrderedDict(fields_defs)
        self.base_fields.keyOrder = attrs_order

        if readonly:
            self.readonly_fields = tuple(attrs_order)

        super(ClassificationForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'

    @property
    def helper(self):
        new_helper = super(ClassificationForm, self).helper
        new_helper.form_show_labels = False
        return new_helper


class ClassifyMultipleForm(forms.Form):
    """Form used to store resources that should be automaticly classified
    when user use proper action in resource classify. Only resouces
    that are assigned to given classification project collection, can be
    used for multiple classification.
    """
    selected_resources = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    def clean_selected_resources(self):
        error_msg = u"Classify multiple resources form has been tempered with."
        collection = self.initial.get('collection', None)
        if not collection:
            raise forms.ValidationError(error_msg)
        selected_resources = self.cleaned_data.get('selected_resources', None)
        resources = Resource.objects.filter(
            pk__in=parse_pks(pks=selected_resources),
            collection=collection.collection.collection
        )
        if not resources:
            raise forms.ValidationError(error_msg)
        return resources


class ClassificationTagForm(BaseCrispyForm):
    """For m used to generate helper form for craeting resource tags
    from list of classifications inside classification project.

    """
    classifications_pks = forms.CharField(
        widget=forms.HiddenInput()
    )

    def __init__(self, *args, **kwargs):
        """Except `classifications_pks` field, all fields are
        :class:`forms.BooleanField` and they are generated dynamically based
        on selected classificator fields.
        """

        form_data = []
        if 'form_data' in kwargs:
            form_data = kwargs.pop('form_data')
            form_data.sort(key=lambda x: x.lower())
        super(ClassificationTagForm, self).__init__(*args, **kwargs)

        for value in form_data:
            self.fields[value] = forms.BooleanField(
                required=False
            )


class ClassificationImportForm(BaseCrispyForm):
    """
    """

    results_csv = forms.FileField(required=True, label='Results table (csv)')

    project = forms.ModelChoiceField(
        queryset=None, required=True,
        label=u'Classification project'
    )
    approve_all = forms.BooleanField(
        initial=False, required=False,
        label=u'Approve all imported classifications'
    )

    def __init__(self, *args, **kwargs):
        """"""

        super(ClassificationImportForm, self).__init__(*args, **kwargs)
        user = get_current_user()
        projects = ClassificationProject.objects.filter(
            classification_project_roles__user=user,
            classification_project_roles__name=1
        ).distinct().order_by('name')
        self.fields['project'].queryset = projects

    def get_layout(self):
        """
        """
        return Layout(
            Fieldset(
                '',
                'project',
                'results_csv',
                'approve_all'
            ),
        )

    def clean(self):
        """
        """
        cleaned_data = self.cleaned_data

        if not self.errors:

            project = cleaned_data.get('project')
            if not project.classificator:
                errors = mark_safe(
                    'The classification project: <strong>{project}</strong> '
                    'has no classificator assigned.'.format(project=project.name)
                )
                raise forms.ValidationError(errors)

            base_attrs = ['id',]
            static_attrs = project.classificator.get_static_attrs_order()
            dynamic_attrs = project.classificator.get_dynamic_attrs_order()
            results_csv = cleaned_data.get('results_csv', None)

            try:
                results_df = pandas.read_csv(results_csv, sep=',', dtype=object)
            except pandas.parser.CParserError:
                errors = mark_safe(
                    'Can not parse file: {file}'.format(file=results_csv.name)
                )
                raise forms.ValidationError(errors)

            headers = base_attrs + static_attrs
            intersection = set(headers).intersection(set(results_df.columns))
            if not len(intersection) == len(headers):
                errors = mark_safe(
                    'Wrong file structure: <strong>{file}</strong>. '
                    .format(
                        file=results_csv.name,
                    )
                )
                raise forms.ValidationError(errors)
            cleaned_data['results_df'] = results_df

        return cleaned_data


class ClassificationExportForm(BaseCrispyForm):
    """
    """

    eml_file = forms.BooleanField(
        initial=False, required=False,
        label=u'EML file',
        help_text='If checked EML (Ecological Metadata Language) file will\
        be generated and included in a data package (zipped).'
    )

    deployments = forms.BooleanField(
        initial=True, required=False,
        label=u'Deployments data',
        help_text='If checked the extra csv file with data on deployments (i.e. period &\
        coordinates) will be generated and included in a data package (zipped).'
    )

    def __init__(self, *args, **kwargs):
        """"""
        super(ClassificationExportForm, self).__init__(*args, **kwargs)

    def get_layout(self):
        """
        """
        return Layout(
            Fieldset(
                '',
                'deployments',
                'eml_file',
            ),
        )


class SequenceBuildForm(BaseCrispyForm):
    """
    """

    time_interval = forms.IntegerField(
        initial=5, required=True,
        help_text='The time interval (minutes) that will be used to automatically \
        group resources into sequences.'
    )

    deployments = forms.BooleanField(
        initial=True, required=False,
        label=u'Aggregate by deployments',
        help_text='If checked resources will be aggregated by deployments.'
    )

    overwrite = forms.BooleanField(
        initial=True, required=False,
        label=u'Overwrite',
        help_text='If checked all existing sequences from selected \
        classification project collections will be overwritten.'
    )

    collections_pks = forms.CharField(
        widget=forms.HiddenInput(),
    )

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'time_interval',
                'deployments',
                'overwrite',
                'collections_pks'
            ),
        )

    def clean_collections_pks(self):
        collections_pks = self.cleaned_data.pop('collections_pks', None)
        if collections_pks:
            pks_list = parse_pks(collections_pks)
            collections = ClassificationProjectCollection.objects.get_accessible(
                role_levels=[ClassificationProjectRoleLevels.ADMIN,]
            ).filter(
                pk__in=pks_list
            )
            if collections:
                self.cleaned_data['project_collections'] = collections
