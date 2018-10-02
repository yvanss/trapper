# -*- coding: utf-8 -*-
import django_filters
from django import forms
from trapper.apps.geomap.models import Location, Deployment, Map
from django.contrib.gis.geos import Polygon, GEOSException, Point
from django.contrib.gis.measure import D
from django.contrib.auth import get_user_model

from trapper.middleware import get_current_user
from trapper.apps.research.models import ResearchProject
from trapper.apps.media_classification.models import ClassificationProject
from trapper.apps.common.tools import parse_pks
from trapper.apps.common.filters import (
    BaseFilterSet, BaseOwnBooleanFilter,
    BaseDateFilter, BaseLocationsMapFilter
)

User = get_user_model()


class BaseFilter(django_filters.Filter):

    def _format_value(self, value):
        return parse_pks(pks=value)


class ResourceFilter(BaseFilter):

    def filter(self, qs, value):
        ids = self._format_value(value)
        if len(ids) <= 0:
            return qs
        qs = qs.filter(
            deployments__resources__pk__in=ids
        ).order_by('id').distinct('id')
        return qs


class CollectionFilter(BaseFilter):

    def filter(self, qs, value):
        ids = self._format_value(value)
        if len(ids) <= 0:
            return qs
        qs = qs.filter(
            deployments__resources__collection__pk__in=ids
        ).order_by('id').distinct('id')
        return qs


class ClassificationFilter(BaseFilter):

    def filter(self, qs, value):
        ids = self._format_value(value)
        if len(ids) <= 0:
            return qs
        qs = qs.filter(
            deployments__resources__classifications__pk__in=ids
        ).order_by('id').distinct('id')
        return qs


class BBFilter(django_filters.Filter):
    field_class = forms.CharField

    def filter(self, qs, value):
        try:
            bbox = value.split(",")
            geom = Polygon.from_bbox(bbox)
        except (ValueError, GEOSException):
            return qs
        qs = qs.filter(coordinates__within=geom)
        return qs


class RadiusFilter(django_filters.Filter):
    field_class = forms.CharField

    def filter(self, qs, value):
        try:
            radius = value.split(",")
            radius = [float(x) for x in radius]
            geom = Point(radius[:2])
        except (ValueError, GEOSException):
            return qs
        qs = qs.filter(
            coordinates__distance_lte=(geom, D(m=radius[-1]))
        )
        return qs


class LocationFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_type="icontains")
    description = django_filters.CharFilter(lookup_type="icontains")
    owner = BaseOwnBooleanFilter()
    owners = django_filters.MultipleChoiceFilter(
        name='owner',
        choices=User.objects.values_list('pk', 'username')
    )
    research_project = django_filters.MultipleChoiceFilter(
        choices=ResearchProject.objects.values_list('pk', 'acronym')
    )
    locations_map = BaseLocationsMapFilter(
        name='pk'
    )
    deployments = django_filters.MethodFilter(action='filter_deployments')

    class Meta:
        model = Location

    def filter_deployments(self, qs, value):
        if value.strip() == "":
            return qs
        ids = parse_pks(pks=value)
        qs = qs.filter(deployments__pk__in=ids)
        return qs


class LocationGeoFilter(LocationFilter):
    research_project = django_filters.ChoiceFilter(
        choices=ResearchProject.objects.values_list('pk', 'acronym')
    )
    locations = BaseLocationsMapFilter(
        name='pk'
    )
    colls = CollectionFilter(name='colls')
    reses = ResourceFilter(name='reses')
    classes = ClassificationFilter(name='classes')
    radius = RadiusFilter()

    class Meta:
        model = Location


# Deployments filters


class DeploymentFilter(BaseFilterSet):
    """Filter used in deployment list view"""

    location = django_filters.MultipleChoiceFilter()
    research_project = django_filters.MultipleChoiceFilter(
        choices=ResearchProject.objects.values_list('pk', 'acronym')
    )
    tags = django_filters.MultipleChoiceFilter()
    owner = BaseOwnBooleanFilter()
    sdate_from = BaseDateFilter(
        name='start_date',
        lookup_type=('gte')
    )
    sdate_to = BaseDateFilter(
        name='start_date',
        lookup_type=('lte')
    )
    edate_from = BaseDateFilter(
        name='end_date',
        lookup_type=('gte')
    )
    edate_to = BaseDateFilter(
        name='end_date',
        lookup_type=('lte')
    )
    classification_project = django_filters.MethodFilter(
        action='filter_cproject'
    )
    correct_setup=django_filters.BooleanFilter()
    correct_tstamp=django_filters.BooleanFilter()

    class Meta:
        model = Deployment

    def __init__(self, *args, **kwargs):
        super(DeploymentFilter, self).__init__(*args, **kwargs)
        # set choices for multiple choice filters
        if self.data.get('location', None):
            self.filters['location'].field.choices = self.queryset.values_list(
                "location__pk",
                "location__location_id"
            ).order_by('id').distinct('id')
        if self.data.get('tags', None):
            self.filters['tags'].field.choices = Deployment.tags.values_list(
                "pk", "name"
            )

    def filter_cproject(self, qs, value):
        try:
            cproject = ClassificationProject.objects.get(pk=value)
        except ClassificationProject.DoesNotExist:
            return ''
        pks = cproject.collections.values_list(
            'collection__resources__deployment', flat=True
        ).distinct()
        return qs.filter(pk__in=pks)


class MapOwnBooleanFilter(django_filters.Filter):
    """Base boolean filter class for limiting queryset to values that are
    owned by currently logged in user """
    field_class = forms.BooleanField

    def filter(self, queryset, value):
        user = get_current_user()
        if value is True:
            # Only owner or manager resources
            queryset = queryset.filter(
                owner=user
            )
        return queryset


class MapFilter(BaseFilterSet):
    """Filter used in map list view"""

    owner = MapOwnBooleanFilter()

    class Meta:
        model = Map
        #exclude = []





