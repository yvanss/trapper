# -*- coding: utf-8 -*-
"""Filters used in storage application when backend is used to
limit data"""

from django import forms
from django.contrib.auth import get_user_model

import django_filters

from trapper.apps.storage.models import Resource, Collection
from trapper.apps.storage.taxonomy import (
    ResourceType, ResourceStatus, CollectionStatus
)
from trapper.apps.research.models import ResearchProject
from trapper.apps.common.filters import (
    BaseFilterSet, BaseOwnBooleanFilter, BaseDateFilter,
    BaseTimeFilter, BaseLocationsMapFilter
)

User = get_user_model()


class CollectionAppend(django_filters.Filter):
    """Filter used to limit collections that can be changed"""
    field_class = forms.BooleanField

    def filter(self, queryset, value):
        if value:
            queryset = Collection.objects.get_editable(
                base_queryset=queryset
            )
        return queryset


class OwnResourceBooleanFilter(BaseOwnBooleanFilter):
    """Filter for owned :class:`apps.storage.models.Resource` model"""
    status_class = ResourceStatus


class OwnCollectionBooleanFilter(BaseOwnBooleanFilter):
    """Filter for owned :class:`apps.storage.models.Collection` model"""
    status_class = CollectionStatus


# Filtersets
class ResourceFilter(BaseFilterSet):
    """Filter used in resource list view"""
    resource_type = django_filters.ChoiceFilter(
        choices=ResourceType.get_all_choices(), label='Type'
    )
    status = django_filters.ChoiceFilter(
        choices=ResourceStatus.get_all_choices()
    )
    rdate_from = BaseDateFilter(
        name='date_recorded', lookup_type=('gte'),
    )
    rdate_to = BaseDateFilter(
        name='date_recorded', lookup_type=('lte'),
    )
    udate_from = BaseDateFilter(
        name='date_uploaded', lookup_type=('gte'),
    )
    udate_to = BaseDateFilter(
        name='date_uploaded', lookup_type=('lte'),
    )
    rtime_from = BaseTimeFilter(
        time_format = '%H:%M',
        name='date_recorded',
        lookup_type='from'
    )
    rtime_to = BaseTimeFilter(
        time_format = '%H:%M',
        name='date_recorded',
        lookup_type='to'
    )
    owner = OwnResourceBooleanFilter(label='My Resources')
    locations_map = BaseLocationsMapFilter(
        name='deployment__location')
    collections = django_filters.MultipleChoiceFilter(
        name="collection", distinct=True
    )
    deployments = django_filters.MultipleChoiceFilter(
        name="deployment", distinct=True
    )
    deployment__isnull = django_filters.BooleanFilter()

    tags = django_filters.MultipleChoiceFilter(
        choices=Resource.tags.values_list("pk", "name")
    )

    class Meta:
        model = Resource
        exclude = [
            'extras_mime_type', 'date_uploaded', 'date_recorded',
        ]

    def __init__(self, *args, **kwargs):
        super(ResourceFilter, self).__init__(*args, **kwargs)
        if self.data.get('deployments', None):
            self.filters['deployments'].field.choices = self.queryset.order_by(
                'deployment').values_list(
                    'deployment__pk',
                    'deployment__deployment_id'
                ).distinct()
        if self.data.get('collections', None):
            self.filters['collections'].field.choices = self.queryset.order_by(
                'collection').values_list(
                    'collection__pk',
                    'collection__name'
                ).distinct()


class CollectionFilter(BaseFilterSet):
    """Filter used in collection list view"""
    status = django_filters.Filter()
    owner = OwnCollectionBooleanFilter(label='My Collections')
    append_collection = CollectionAppend()

    research_projects = django_filters.MultipleChoiceFilter(
        name='research_projects',
        choices=ResearchProject.objects.values_list('pk', 'name')
    )
    owners = django_filters.MultipleChoiceFilter(
        name='owner',
        choices=User.objects.values_list('pk', 'username')
    )
    locations_map = BaseLocationsMapFilter(
        name='resources__deployment__location')

    class Meta:
        model = Collection
        exclude = [
            'date_created', 'description',
        ]
