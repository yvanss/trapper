# -*- coding: utf-8 -*-
"""Filters used in media classification application when backend is used to
limit data"""
import json

import django_filters
from django import forms
from django.db.models import Q

from trapper.apps.storage.models import Resource
from trapper.apps.storage.taxonomy import ResourceType
from trapper.apps.media_classification.models import (
    Classification, Classificator, ClassificationProjectCollection,
    UserClassification, ClassificationProject, Sequence
)
from trapper.apps.media_classification.taxonomy import (
    ClassificationProjectRoleLevels
)
from trapper.apps.common.filters import (
    BaseFilterSet, BaseOwnBooleanFilter,
    BaseDateFilter, BaseTimeFilter,
    BaseLocationsMapFilter
)


class ClassificationProjectFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.ClassificationProject` model
    when backend filtering is used
    """
    owner = BaseOwnBooleanFilter(
        managers=False,
        role_levels=ClassificationProjectRoleLevels.UPDATE,
        role_field='classification_project_roles'
    )
    research_project = django_filters.Filter(
        name="research_project"
    )

    class Meta:
        model = ClassificationProject
        fields = ['owner', 'status', 'research_project']


class HstoreAttrsFilter(django_filters.filters.Filter):
    """Filter field used for simple filtering of hstore values"""
    field_class = forms.CharField

    def filter(self, qs, value):
        if value:
            return qs.filter(
                Q(static_attrs__contains={self.name: value}) |
                Q(dynamic_attrs__attrs__contains={self.name: value})
            ).distinct()
        return qs


class ClassificationFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.Classification` model
    when backend filtering is used
    """
    owner = BaseOwnBooleanFilter(
        owner_field='resource__owner',
        managers_field='resource__managers',
        managers=True
    )

    deployment = django_filters.MultipleChoiceFilter(
        name='resource__deployment'
    )
    collection = django_filters.MultipleChoiceFilter(
        name='collection'
    )
    locations_map = BaseLocationsMapFilter(
        name='resource__deployment__location')
    project = django_filters.Filter(name='project__pk')
    status = django_filters.BooleanFilter()
    rdate_from = BaseDateFilter(
        name='resource__date_recorded',
        lookup_type=('gte')
    )
    rdate_to = BaseDateFilter(
        name='resource__date_recorded',
        lookup_type=('lte')
    )
    rtime_from = BaseTimeFilter(
        time_format = '%H:%M',
        name='resource__date_recorded',
        lookup_type='from'
    )
    rtime_to = BaseTimeFilter(
        time_format = '%H:%M',
        name='resource__date_recorded',
        lookup_type='to'
    )
    ftype = django_filters.ChoiceFilter(
        name='resource__resource_type',
        choices=ResourceType.get_all_choices() 
    )

    class Meta:
        model = Classification
        exclude = [
            'created_at', 'updated_at', 'updated_by',
            'approved_by', 'approved_at', 'approved_source'
        ]

    def __init__(self, *args, **kwargs):
        super(ClassificationFilter, self).__init__(*args, **kwargs)
        project_pk = self.data.get('project', None)
        if project_pk:
            c = ClassificationProject.objects.get(pk=project_pk).classificator        
            if c:
                class_attrs = [k for l in c.get_all_attrs_names() for k in l]
                for a in class_attrs:
                    if self.data.get(a) and a in class_attrs:
                        self.filters[a] = HstoreAttrsFilter(name=a)
        # set choices for multiple choice filters
        if self.data.get('collection', None):
            self.filters['collection'].field.choices = self.queryset.order_by(
                'collection').values_list(
                    'collection__pk',
                    'collection__collection__collection__name'
                ).distinct()
        if self.data.get('deployment', None):
            self.filters['deployment'].field.choices = self.queryset.order_by(
                'resource__deployment').values_list(
                    'resource__deployment__pk',
                    'resource__deployment__deployment_id'
                ).distinct()


class UserClassificationFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.UserClassification` model
    when backend filtering is used
    """
    user = django_filters.MultipleChoiceFilter(
        name='owner'
    )
    owner = BaseOwnBooleanFilter(managers=False)
    deployment = django_filters.MultipleChoiceFilter(
        name='classification__resource__deployment'
    )
    collection = django_filters.MultipleChoiceFilter(
        name='classification__collection'
    )
    approved = django_filters.MethodFilter(action='filter_approved')
    locations_map = BaseLocationsMapFilter(
        name='classification__resource__deployment__location')
    project = django_filters.Filter(name='classification__project__pk')
    rdate_from = BaseDateFilter(
        name='classification__resource__date_recorded',
        lookup_type=('gte')
    )
    rdate_to = BaseDateFilter(
        name='classification__resource__date_recorded',
        lookup_type=('lte')
    )
    rtime_from = BaseTimeFilter(
        time_format = '%H:%M',
        name='classification__resource__date_recorded',
        lookup_type='from'
    )
    rtime_to = BaseTimeFilter(
        time_format = '%H:%M',
        name='classification__resource__date_recorded',
        lookup_type='to'
    )

    class Meta:
        model = UserClassification
        exclude = [
            'created_at', 'updated_at', 'updated_by',
        ]

    def __init__(self, *args, **kwargs):
        super(UserClassificationFilter, self).__init__(*args, **kwargs)
        # set choices for multiple choice filters
        if self.data.get('user', None):
            self.filters['user'].field.choices = self.queryset.order_by(
                'owner__username').values_list(
                    'owner__pk',
                    'owner__username'
                ).distinct()
        if self.data.get('collection', None):
            self.filters['collection'].field.choices = self.queryset.order_by(
                'classification__collection').values_list(
                    'classification__collection__pk',
                    'classification__collection__collection__collection__name'
                ).distinct()
        if self.data.get('deployment', None):
            self.filters['deployment'].field.choices = self.queryset.order_by(
                'classification__resource__deployment').values_list(
                    'classification__resource__deployment__pk',
                    'classification__resource__deployment__deployment_id'
                ).distinct()

    def filter_approved(self, qs, value):
        if value in ['True', 'true']:
            value = True
        elif value in ['False', 'false']:
            value = False
        else:
            return qs
        return qs.exclude(classification_approved__isnull=value)


class ClassificatorFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.Classificator` model
    when backend filtering is used
    """
    owner = BaseOwnBooleanFilter(managers=False)
    owners = django_filters.MultipleChoiceFilter(
        name='owner'
    )
    udate_from = BaseDateFilter(
        name='updated_date',
        lookup_type=('gte')
    )
    udate_to = BaseDateFilter(
        name='updated_date',
        lookup_type=('lte')
    )

    class Meta:
        model = Classificator
        exclude = [
            'dynamic_attrs_order', 'static_attrs_order', 'updated_date',
            'created_date', 'description', 'copy_of', 'disabled_at',
            'disabled_by', 'updated'
        ]

    def __init__(self, *args, **kwargs):
        super(ClassificatorFilter, self).__init__(*args, **kwargs)
        # set choices for multiple choice filters
        self.filters['owners'].field.choices = self.queryset.values_list(
            'owner__pk',
            'owner__username'
        ).distinct()


class ClassificationProjectCollectionFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.ClassificationProjectCollection`
    model when backend filtering is used
    """
    class Meta:
        model = ClassificationProjectCollection

    owner = BaseOwnBooleanFilter(
        owner_field='collection__collection__owner',
        managers_field='collection__collection__managers',
    )
    owners = django_filters.MultipleChoiceFilter(
        name='collection__collection__owner'
    )
    status = django_filters.Filter(
        name='collection__collection__status'
    )

    def __init__(self, *args, **kwargs):
        super(ClassificationProjectCollectionFilter, self).__init__(*args, **kwargs)
        # set choices for multiple choice filters
        if self.data.get('owners', None):
            self.filters['owners'].field.choices = self.queryset.order_by(
                'collection__collection__owner'
            ).values_list(
                'collection__collection__owner__pk',
                'collection__collection__owner__username'
            ).distinct()


class SequenceFilter(BaseFilterSet):
    """Filter for
    :class:`apps.media_classification.models.Sequence` model when backend
    filtering is used
    """

    deployment = django_filters.MethodFilter(action='filter_deployment')

    class Meta:
        model = Sequence
        exclude = [
            'description', 'created_at', 'created_by'
        ]

    def filter_deployment(self, qs, value):
        pks = self.format_pks(value)
        if not pks:
            return qs
        return qs.filter(resources__deployment__pk__in=pks).distinct()
