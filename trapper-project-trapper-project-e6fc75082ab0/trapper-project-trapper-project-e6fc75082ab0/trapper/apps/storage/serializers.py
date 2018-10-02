# -*- coding: utf-8 -*-
"""Serializers used with storage application for DRF"""

import itertools

from django.core.urlresolvers import reverse
from rest_framework import serializers

from trapper.apps.storage.models import Resource, Collection, TaggedResource
from trapper.apps.common.serializers import BasePKSerializer, PrettyUserField


class ResourceNestedSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource` used within other
    serializers that are connected (mostly through fk) to
    :class:`apps.storage.models.Resource` model instances"""

    class Meta:
        model = Resource
        fields = ('name', 'owner', 'url')

    owner = PrettyUserField()
    url = serializers.ReadOnlyField(source='get_absolute_url')


class ResourceSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource`
    Serializer contains urls for details/delete/update resource if user
    has enough permissions
    """

    class Meta:
        model = Resource
        fields = (
            'pk', 'name', 'owner', 'owner_profile',
            'resource_type', 'date_recorded', 'tags',
            'url', 'mime', 'extra_url', 'extra_mime',
            'thumbnail_url',

            # data for action columns
            'update_data', 'detail_data', 'delete_data',
            'date_recorded_correct'
        )

    name = serializers.ReadOnlyField(source='prefixed_name')
    date_recorded = serializers.ReadOnlyField(source='date_recorded_tz')
    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField('get_profile')
    url = serializers.ReadOnlyField(source='get_url')
    mime = serializers.ReadOnlyField(source='mime_type')
    extra_url = serializers.ReadOnlyField(source='get_extra_url')
    extra_mime = serializers.ReadOnlyField(source='extra_mime_type')
    thumbnail_url = serializers.ReadOnlyField(source='get_thumbnail_url')

    tags = serializers.SerializerMethodField()

    update_data = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()
    date_recorded_correct = serializers.ReadOnlyField(source='check_date_recorded')

    def get_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_update_data(self, item):
        """Custom method for retrieving update url"""
        return Resource.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Resource.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return Resource.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )

    def get_tags(self, obj):
        """Custom method for retrieving resource tags"""
        if not getattr(self, 'tags_dict', None):
            pks = [k.pk for k in self.instance]
            tags_values = TaggedResource.objects.filter(
                content_object__pk__in=pks
            ).values_list('content_object__pk', 'tag__name')
            self.tags_dict = {
                k:list(x[1] for x in v) for k,v in itertools.groupby(
                    sorted(tags_values), key=lambda x: x[0]
                )
            }
        tags = self.tags_dict.get(obj.pk)
        return tags


class ResourceMapSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource` used
    by the map view.
    """

    class Meta:
        model = Resource
        fields = (
            'pk', 'name', 'resource_type', 'deployment',
            'date_recorded', 'tags', 'thumbnail_url',
            'detail_data'
        )

    name = serializers.ReadOnlyField(source='prefixed_name')
    date_recorded = serializers.ReadOnlyField(source='date_recorded_tz')
    deployment = serializers.ReadOnlyField(source='deployment.deployment_id')
    thumbnail_url = serializers.ReadOnlyField(source='get_thumbnail_url')
    tags = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Resource.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_tags(self, obj):
        """Custom method for retrieving resource tags"""
        return [k.name for k in obj.tags.all()]


class CollectionSerializer(BasePKSerializer):
    """Serializer for :class:`storage.Collection`

    Serializer contains urls for details/delete/update collection if user
    has enough permissions
    """

    class Meta:
        model = Collection
        fields = (
            'pk', 'name', 'owner', 'owner_profile', 'status',
            'description',

            'update_data', 'detail_data', 'delete_data',
            'ask_access_data',
        )

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()

    update_data = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()
    ask_access_data = serializers.SerializerMethodField()

    def get_owner_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_update_data(self, item):
        """Custom method for retrieving update url"""
        return Collection.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Collection.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return Collection.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )

    def get_ask_access_data(self, item):
        """Custom method for retrieving collection request url"""
        return Collection.objects.api_ask_access_context(
            item=item,
            user=self.context['request'].user
        )


class CollectionAppendSerializer(BasePKSerializer):

    class Meta:
        model = Collection
        fields = ('pk', 'name')
