# -*- coding: utf-8 -*-
"""Filters used in research application when backend is used to
limit data"""
import django_filters

from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.research.taxonomy import ResearchProjectRoleType
from trapper.apps.common.filters import BaseFilterSet, BaseOwnBooleanFilter


class ResearchProjectFilter(BaseFilterSet):
    """Filter for owned :class:`apps.research.models.ResearchProject` model"""
    owner = BaseOwnBooleanFilter(
        managers=False,
        role_levels=ResearchProjectRoleType.EDIT
    )
    keywords = django_filters.MultipleChoiceFilter()

    class Meta:
        model = ResearchProject

    def __init__(self, *args, **kwargs):
        super(ResearchProjectFilter, self).__init__(*args, **kwargs)
        self.filters['keywords'].field.choices = ResearchProject.keywords.values_list(
            "pk", "name"
        )


class ResearchProjectCollectionFilter(BaseFilterSet):
    """Filter for owned
    :class:`apps.research.models.ResearchProjectCollection` model"""

    owner = BaseOwnBooleanFilter(
        owner_field='collection__owner',
        managers_field='collection__managers',
    )
    owners = django_filters.MultipleChoiceFilter(
        name='collection__owner'
    )
    status = django_filters.Filter(
        name='collection__status'
    )

    class Meta:
        model = ResearchProjectCollection

    def __init__(self, *args, **kwargs):
        super(ResearchProjectCollectionFilter, self).__init__(*args, **kwargs)
        # set choices for multiple choice filters
        self.filters['owners'].field.choices = set(self.queryset.values_list(
            'collection__owner__pk',
            'collection__owner__username'
        ))
