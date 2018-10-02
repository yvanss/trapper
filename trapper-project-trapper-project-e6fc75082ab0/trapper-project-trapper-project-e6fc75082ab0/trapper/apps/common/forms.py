# -*- coding: utf-8 -*-
"""Commonly used extensions for forms"""

from django import forms
from django.db.models import Q
from django.forms.models import BaseInlineFormSet
from django.forms.fields import FileField
from django.core.exceptions import ValidationError

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field

from trapper.middleware import get_current_user
from trapper.apps.common.tools import parse_pks


class CrispyFormMixin(object):
    """Standard helper for forms that want to use crispy tags
    This mixin add helper property.

    Layout can be specified by overwritting get_layout method
    """
    form_style = 'default'
    field_template = 'crispy_forms/bootstrap3/field.html'

    def get_layout(self):
        """Define layout for crispy form helper"""
        return

    @property
    def helper(self):
        """Default helper that is used by crispy forms"""
        helper = FormHelper()
        helper.form_tag = False
        helper.form_style = self.form_style
        helper.field_template = self.field_template
        layout = self.get_layout()

        if layout:
            helper.layout = layout

        # add 'select2-default 'class to all fields
        # specified in form.select2_fields
        select2_fields = getattr(self, 'select2_fields', None)
        if select2_fields:
            for field in select2_fields:
                helper[field].wrap(
                    Field, css_class="select2-default form-control"
                )

        return helper


class ReadOnlyFieldsMixin(object):
    """Mixin used to mark all fields in form as readonly"""
    readonly_fields = ()

    def __init__(self, *args, **kwargs):
        super(ReadOnlyFieldsMixin, self).__init__(*args, **kwargs)
        """Check if field is not disabled and then make it not required"""
        for field in (
            field for name, field in self.fields.iteritems()
            if name in self.readonly_fields
        ):
            field.widget.attrs['disabled'] = 'true'
            field.required = False

    def clean(self):
        """All fields that are disabled should not be able to overwrite
        value stored on instance"""
        cleaned_data = super(ReadOnlyFieldsMixin, self).clean()
        for field in self.readonly_fields:
            cleaned_data[field] = getattr(self.instance, field)
        return cleaned_data


class BaseUnicodeFormMixin(object):
    """Mixin that fixes unicode form field names.
    Such fields are used i.e. in media classification when user
    can define classificator form.

    .. warning::
        This mixin is not `Python 3.x` compatibile
    """
    def _clean_fields(self):
        """Method called by :func:`clean` form method. This method fixes
        issues with handling non-ascii form field names that can be
        generated using dynamically created forms

        .. warning::
            This method is not `Python 3.x` compatibile
        """
        for name, field in self.fields.items():
            # value_from_datadict() gets the data from the data dictionaries.
            # Each widget type knows how to retrieve its own data, because some
            # widgets split data over several HTML fields.
            value = field.widget.value_from_datadict(
                self.data, self.files, self.add_prefix(name)
            )
            try:
                if isinstance(field, FileField):
                    initial = self.initial.get(name, field.initial)
                    value = field.clean(value, initial)
                else:
                    value = field.clean(value)
                self.cleaned_data[name] = value
                field_name = u'clean_{name}'.format(name=name)
                # Fix for issues with unicode field names that django can't
                # handle properly
                try:
                    if hasattr(self, field_name):
                        value = getattr(self, field_name)()
                        self.cleaned_data[name] = value
                except (UnicodeDecodeError, UnicodeEncodeError):
                    pass
            except ValidationError as e:
                self._errors[name] = self.error_class(e.messages)
                if name in self.cleaned_data:
                    del self.cleaned_data[name]


class BaseCrispyForm(BaseUnicodeFormMixin, CrispyFormMixin, forms.Form):
    """Django non-model form version that is unicode field name safe and
    support crispy"""
    pass


class BaseCrispyModelForm(
    BaseUnicodeFormMixin, CrispyFormMixin, forms.ModelForm
):
    """Django model form version that is unicode field name safe and
    support crispy"""
    pass


class BaseBulkUpdateForm(BaseCrispyModelForm):
    """
    """
    records_pks = forms.CharField(
        widget=forms.HiddenInput()
    )

    select2_fields = ()

    @property
    def helper(self):
        helper = super(BaseBulkUpdateForm, self).helper
        for field in self.fields:
            if field == 'records_pks':
                continue
            css_class = 'controlled'
            if field in self.select2_fields:
                css_class = 'select2-default controlled'
            helper[field].wrap(
                Field,
                css_class=css_class,
                disabled=True,
                template='forms/field_with_locker.html'
            )
        return helper

    def __init__(self, *args, **kwargs):
        super(BaseBulkUpdateForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False

    def filter_editable(self):
        user = get_current_user()
        records = self.Meta.model.objects.filter(
            Q(owner=user) | Q(managers=user)
        )
        return records

    def clean_records_pks(self):
        records_pks = self.cleaned_data.pop('records_pks', None)
        if records_pks:
            pks_list = parse_pks(records_pks)
            records = self.filter_editable()
            records = records.filter(pk__in=pks_list)
            if records:
                self.cleaned_data['records'] = records

    def clean(self):
        cleaned_data = super(BaseBulkUpdateForm, self).clean()
        # check which fields have been posted; if no checkboxes have
        # been selected (self.data.keys < 3) raise validation error
        posted_fields = self.data.keys()
        if len(posted_fields) < 3:
            raise forms.ValidationError(
                'You have to provide some data to bulk update '
                'the selected records.'
            )
        new_cleaned_data = {}
        for field in cleaned_data:
            if field in posted_fields or field == 'records':
                new_cleaned_data[field] = cleaned_data[field]
        return new_cleaned_data


class ProjectBaseInlineFormSet(BaseInlineFormSet):
    def clean(self):
        """Check for duplicate project roles."""
        if any(self.errors):
            return
        pairs = []
        for form in self.forms:
            user = form.cleaned_data.get('user', None)
            project = form.cleaned_data.get('project', None)
            if not (user or project):
                continue
            if (user, project) in pairs:
                msg = 'This user already has a role in this project.'
                errors = form._errors.setdefault('user', form.error_class())
                errors.append(msg)
            pairs.append((user, project))
