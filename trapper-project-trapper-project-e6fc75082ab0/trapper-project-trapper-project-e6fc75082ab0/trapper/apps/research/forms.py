# -*- coding: utf-8 -*-
"""Forms used by research application.

This module contains forms mainly related to
:class:`apps.research.models.ResearchProject`,
:class:`apps.research.models.ResearchProjectCollection` and
:class:`apps.research.models.ResearchProjectRole` models
"""
from __future__ import unicode_literals

from django import forms
from django.contrib.auth import get_user_model

from crispy_forms.helper import FormHelper
from extra_views import InlineFormSet
from crispy_forms.layout import Layout, Fieldset, HTML
from taggit.forms import TagField

from trapper.apps.research.models import (
    ResearchProject, ResearchProjectRole, ResearchProjectCollection
)
from trapper.apps.research.taxonomy import ResearchProjectRoleType
from trapper.apps.common.forms import (
    BaseCrispyModelForm, ProjectBaseInlineFormSet
)
from trapper.apps.common.fields import OwnerModelChoiceField

User = get_user_model()


class ResearchProjectForm(BaseCrispyModelForm):
    """
    Model form for creating or updating
    :class:`apps.research.models.ResearchProject` objects
    """

    keywords = TagField(required=False)

    class Meta:
        model = ResearchProject
        exclude = ['project_roles', 'owner', 'status', 'collections']

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'name',
                'acronym',
                'keywords',
                'abstract',
                'methods',
                'description',
                HTML('{% include "research/project_role_formset.html" %}'),
            ),
        )

    def __init__(self, **kwargs):
        """:class:`ResearchProjectForm` contains few textarea fields that
        by default should be collapsed"""
        super(ResearchProjectForm, self).__init__(**kwargs)

        self.fields['description'].label_css = 'collapsable'
        self.fields['abstract'].label_css = 'collapsable'
        self.fields['methods'].label_css = 'collapsable'
        if 'keywords' in self.fields:
            keywords = ",".join(ResearchProject.keywords.values_list('name', flat=True))
            self.fields['keywords'].widget.attrs['data-tags'] = keywords


class ProjectCollectionForm(forms.ModelForm):
    """
    Model form for creating or updating
    :class:`apps.research.models.ResearchProjectCollection` objects
    """

    class Meta:
        model = ResearchProjectCollection
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        """If user is passed as kwarg argument, then research projects
        should be limited to those, that can be updated"""
        user = kwargs.pop('user', None)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.error_text_inline = True
        self.helper.form_show_errors = True
        self.helper.help_text_inline = False
        super(ProjectCollectionForm, self).__init__(*args, **kwargs)
        self.fields['collection'].widget = forms.HiddenInput()
        if user:
            project_pks = set(
                role.project.pk for role in user.research_roles.filter(
                    name__in=ResearchProjectRoleType.EDIT
                )
            )
            projects = ResearchProject.objects.filter(pk__in=project_pks)
            self.fields['project'].queryset = projects

    def clean(self):
        """
        Collection should nod be added to the same research project more than
        once
        """
        project = self.cleaned_data.get("project")
        collection = self.cleaned_data.get("collection")
        if ResearchProjectCollection.objects.filter(
                project=project, collection=collection
        ):
            raise forms.ValidationError("Project Collection already exists.")
        return self.cleaned_data


class ProjectRoleForm(BaseCrispyModelForm):
    """
    Model form for creating or updating
    :class:`apps.research.models.ResearchProjectRole` objects
    """
    form_style = 'inline'
    user = OwnerModelChoiceField(queryset=User.objects.all())

    class Meta:
        model = ResearchProjectRole
        exclude = ['project', 'date_created']

    def __init__(self, *args, **kwargs):
        """Remove labels for formset"""
        super(ProjectRoleForm, self).__init__(*args, **kwargs)
        self.fields['user'].label = ''
        self.fields['user'].widget.attrs['class'] = 'select2-default form-control'
        self.fields['name'].label = ''


class ProjectRoleInline(InlineFormSet):
    """Utility-class: ProjectRoles displayed as a InlineFormset"""
    model = ResearchProjectRole
    form_class = ProjectRoleForm
    formset_class = ProjectBaseInlineFormSet
    extra = 1
