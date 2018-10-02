# -*- coding: utf-8 -*-
"""Serializers used with research application for DRF"""

from django.core.urlresolvers import reverse

from rest_framework import serializers

from trapper.apps.storage.models import Collection
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.common.serializers import BasePKSerializer, PrettyUserField
from trapper.apps.accounts.utils import get_pretty_username


class CollectionsNestedSerializer(BasePKSerializer):
    """Serializer for :class:`apps.research.models.ResearchProjectCollection`
    that is used by :class:`ResearchProjectSerializer`
    """

    class Meta:
        model = Collection
        fields = ('name', 'url')

    url = serializers.ReadOnlyField(source='get_absolute_url')


class ResearchProjectSerializer(BasePKSerializer):
    """Serializer for :class:`apps.research.models.ResearchProject`
    Serializer contains urls for details/delete/update project if user
    has enough permissions
    """

    class Meta:
        model = ResearchProject
        fields = (
            'pk', 'name', 'owner', 'owner_profile',
            'acronym', 'keywords', 'date_created', 'project_roles',
            'update_data', 'detail_data', 'delete_data', 'status',
        )

    project_roles = serializers.SerializerMethodField('get_roles')
    keywords = serializers.SerializerMethodField()

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()

    update_data = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()

    def get_owner_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_update_data(self, item):
        """Custom method for retrieving update url"""
        return ResearchProject.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return ResearchProject.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return ResearchProject.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )

    def get_roles(self, item):
        roles_list = []
        for user, role_list in item.get_roles().items():
            roles = [role.get_name_display() for role in role_list]
            roles.sort()
            roles_list.append({
                'user': get_pretty_username(user=user),
                'profile': reverse(
                    'accounts:show_profile', kwargs={'username': user.username}
                ),
                'roles': roles
            })
        roles_list.sort(key=lambda x: x['user'])
        return roles_list

    def get_keywords(self, obj):
        """Custom method for retrieving project keywords"""
        return [k.name for k in obj.keywords.all()]


class ResearchProjectCollectionSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.ResearchProjectCollection`
    Serializer contains urls for details/delete project collections if user
    has enough permissions
    """

    class Meta:
        model = ResearchProjectCollection
        fields = (
            'pk', 'collection_pk', 'name', 'owner', 'owner_profile', 'status', 
            'date_created', 'description', 'detail_data', 'delete_data',
        )

    name = serializers.ReadOnlyField(source='collection.name')
    collection_pk = serializers.ReadOnlyField(source='collection.pk')
    status = serializers.ReadOnlyField(source='collection.status')
    date_created = serializers.ReadOnlyField(source='collection.date_created')
    description = serializers.ReadOnlyField(source='collection.description')
    owner = PrettyUserField(source='collection.owner')
    owner_profile = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()

    def get_owner_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile',
            kwargs={'username': item.collection.owner.username}
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Collection.objects.api_detail_context(
            item=item.collection,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return ResearchProjectCollection.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )
