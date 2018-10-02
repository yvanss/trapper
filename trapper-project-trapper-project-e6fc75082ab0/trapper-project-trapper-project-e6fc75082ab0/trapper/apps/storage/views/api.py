# -*- coding: utf-8 -*-
"""Views used by DRF to display json data used by storage aapplications"""

from trapper.apps.storage.models import Resource, Collection
from trapper.apps.storage import serializers as storage_serializers
from trapper.apps.storage.filters import ResourceFilter, CollectionFilter
from trapper.apps.common.views_api import PaginatedReadOnlyModelViewSet


class ResourceViewSet(PaginatedReadOnlyModelViewSet):
    """Return list of resources.

    * For anonymous users return only publicly available resources
    * For logged in users return resources that are available for user
    """
    serializer_class = storage_serializers.ResourceSerializer
    filter_class = ResourceFilter
    search_fields = ['name', 'owner__username', 'custom_prefix', 'tags__name']

    def get_queryset(self):
        return Resource.objects.get_accessible(self.request.user).select_related(
            'owner', 'deployment__location__timezone',
        ).prefetch_related('managers')        


class ResourceMapViewSet(ResourceViewSet):
    pagination_class = None
    serializer_class = storage_serializers.ResourceMapSerializer


class CollectionViewSet(PaginatedReadOnlyModelViewSet):
    """Return list of collections.

    * For anonymous users return only publicly available resources
    * For logged in users return resources that are available for user
    """
    serializer_class = storage_serializers.CollectionSerializer
    filter_class = CollectionFilter
    search_fields = ['name', 'owner__username']

    def get_queryset(self):
        """Limit collections depend on user login status"""
        return Collection.objects.get_accessible(self.request.user).select_related(
            'owner'
        ).prefetch_related('managers')


class CollectionOnDemandViewSet(CollectionViewSet):
    def get_queryset(self):
        """Limit collections depend on user login status"""
        return Collection.objects.get_ondemand(user=self.request.user)


class CollectionMapViewSet(CollectionViewSet):
    pagination_class = None


class CollectionAppendViewSet(CollectionViewSet):
    pagination_class = None
    serializer_class = storage_serializers.CollectionAppendSerializer

    def get_queryset(self):
        user = self.request.user
        return Collection.objects.get_editable(user=user)
