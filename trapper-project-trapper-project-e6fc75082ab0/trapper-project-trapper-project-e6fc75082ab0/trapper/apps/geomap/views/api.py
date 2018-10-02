# -*- coding: utf-8 -*-
import StringIO
import pandas

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from rest_framework.filters import DjangoFilterBackend
from rest_framework_gis.filters import InBBoxFilter
from leaflet_storage.models import Map

from trapper.apps.geomap import serializers as geomap_serializers
from trapper.apps.geomap.filters import (
    LocationFilter, LocationGeoFilter, DeploymentFilter, MapFilter
)
from trapper.apps.geomap.models import Location, Deployment, MapManagerUtils
from trapper.apps.common.views_api import (
    PaginatedReadOnlyModelViewSet, PlainTextRenderer
)
from trapper.apps.common.filters import RegExpSearchFilter


class LocationViewSet(PaginatedReadOnlyModelViewSet):
    queryset = Location.objects.all()
    serializer_class = geomap_serializers.LocationSerializer
    filter_class = LocationFilter
    search_fields = ['location_id', 'name', 'description', 'county', 'city', 'owner__username']
    select_related = [
        'research_project', 'owner',
    ]

    def get_queryset(self):
        queryset = Location.objects.get_available(
            user=self.request.user
        ).select_related(
            *self.select_related
        ).prefetch_related(
            'managers'
        )

        return queryset


class LocationGeoViewSet(ListAPIView):
    serializer_class = geomap_serializers.LocationGeoSerializer
    filter_class = LocationGeoFilter
    search_fields = [
        'location_id', 'name', 'description', 'county', 'city', 'owner__username',
        'deployments__deployment_id'
    ]
    bbox_filter_field = 'coordinates'
    filter_backends = (
        RegExpSearchFilter,
        DjangoFilterBackend,
        InBBoxFilter,
    )

    def get_queryset(self):
        queryset = Location.objects.get_available(
            user=self.request.user
        )
        return queryset


class DeploymentViewSet(PaginatedReadOnlyModelViewSet):
    queryset = Deployment.objects.all()
    serializer_class = geomap_serializers.DeploymentSerializer
    filter_class = DeploymentFilter
    search_fields = ['deployment_id', 'owner__username']
    select_related = [
        'location', 'owner', 'research_project',
    ]
    prefetch_related = ['managers', 'tags']

    def get_queryset(self):
        base_queryset = super(DeploymentViewSet, self).get_queryset()
        queryset = Deployment.objects.get_accessible(
            base_queryset=base_queryset, user=self.request.user
        ).prefetch_related(
            *self.prefetch_related
        ).select_related(
            *self.select_related
        )
        return queryset


class MapViewSet(PaginatedReadOnlyModelViewSet):
    queryset = Map.objects.all()
    serializer_class = geomap_serializers.MapSerializer
    filter_class = MapFilter
    search_fields = ['name', 'description', 'owner__username']
    select_related = ['owner',]

    def get_queryset(self):
        queryset = MapManagerUtils.get_accessible(user=self.request.user)
        qs = queryset.select_related(
            *self.select_related
        )
        return qs


class LocationTableView(ListAPIView):
    """Returns a table with locations.
    """
    permission_classes = (permissions.IsAuthenticated, )
    serializer_class = geomap_serializers.LocationTableSerializer
    pagination_class = None
    filter_class = LocationFilter
    search_fields = [
        'location_id', 'name', 'description', 'country',
        'state', 'county', 'city'
    ]
    sort_by = ['research_project', 'location_id']
    renderer_classes = (PlainTextRenderer, )

    def get_queryset(self):
        queryset = Location.objects.get_available(
            user=self.request.user
        )
        return queryset

    def get_columns_order(self):
        return self.serializer_class.Meta.fields[1:]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = StringIO.StringIO()
        serializer = self.get_serializer(queryset, many=True)    
        df = pandas.DataFrame.from_records(
            serializer.data, columns=self.get_columns_order()
        )
        df = df.sort(self.sort_by)
        df = df.reset_index(drop=True)
        df.to_csv(data, encoding='utf-8', index=False)
        return Response(data.getvalue())


class DeploymentTableView(ListAPIView):
    """Returns a table with deployments.
    """
    permission_classes = (permissions.IsAuthenticated, )
    serializer_class = geomap_serializers.DeploymentTableSerializer
    pagination_class = None
    filter_class = DeploymentFilter
    search_fields = ['deployment_id', 'owner__username']
    sort_by = ['research_project', 'deployment_id']
    renderer_classes = (PlainTextRenderer, )

    def get_queryset(self):
        queryset = Deployment.objects.get_accessible(
            user=self.request.user
        ).select_related(
            'location__timezone',
        )
        return queryset

    def get_columns_order(self):
        return self.serializer_class.Meta.fields

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = StringIO.StringIO()
        serializer = self.get_serializer(queryset, many=True)    
        df = pandas.DataFrame.from_records(
            serializer.data, columns=self.get_columns_order()
        )
        df = df.sort(self.sort_by)
        df = df.reset_index(drop=True)
        df.to_csv(data, encoding='utf-8', index=False)
        return Response(data.getvalue())

