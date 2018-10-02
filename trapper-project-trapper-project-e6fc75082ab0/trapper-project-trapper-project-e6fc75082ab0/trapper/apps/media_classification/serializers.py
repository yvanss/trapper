# -*- coding: utf-8 -*-
"""Serializers used with media classification application for DRF"""

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from rest_framework import serializers

from trapper.apps.common.serializers import (
    BasePKSerializer, PrettyUserField
)
from trapper.apps.storage.models import Resource, Collection
from trapper.apps.media_classification.models import (
    UserClassification, ClassificationProject, Classificator,
    Classification, ClassificationProjectCollection, Sequence
)
from trapper.apps.accounts.utils import get_pretty_username

User = get_user_model()


class UserNestedSerializer(BasePKSerializer):
    """Serializer for :class:`auth.User`that is used by
    :class:`apps.media_classification.models.Sequence`
    """
    class Meta:
        model = User
        fields = ('name', 'url')

    name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField('get_profile')

    def get_name(self, item):
        """Custom method for retrieving prettified username"""
        return get_pretty_username(user=item)

    def get_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile', kwargs={'username': item.username}
        )


class ResourceNestedSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource`
    that is used by :class:`UserClassificationSerializer` and
    :class:`ClassificationSerializer`
    """

    class Meta:
        model = Resource
        fields = (
            'pk', 'name', 'resource_type', 'thumbnail_url',
            'url', 'mime', 'extra_url', 'extra_mime',
            'date_recorded', 'deployment'
        )

    date_recorded = serializers.ReadOnlyField(source='date_recorded_tz')
    deployment = serializers.ReadOnlyField(source='deployment_id')
    url = serializers.ReadOnlyField(source='get_url')
    mime = serializers.ReadOnlyField(source='mime_type')
    extra_url = serializers.ReadOnlyField(source='get_extra_url')
    extra_mime = serializers.ReadOnlyField(source='extra_mime_type')
    thumbnail_url = serializers.ReadOnlyField(source='get_thumbnail_url')

    def get_resource_url(self, item):
        """Custom method for retrieving resource file url"""
        if item.file:
            return item.file.url


class ResourceNestedMapSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource`
    that is used by :class:`UserClassificationSerializer` and
    :class:`ClassificationSerializer`
    """

    class Meta:
        model = Resource
        fields = (
            'pk', 'name', 'resource_type', 'thumbnail_url',
            'date_recorded', 'deployment'
        )

    date_recorded = serializers.ReadOnlyField(source='date_recorded_tz')
    deployment = serializers.ReadOnlyField(source='deployment.deployment_id')
    thumbnail_url = serializers.ReadOnlyField(source='get_thumbnail_url')


class CollectionNestedSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Collection`
    that is used by :class:`ClassificationSerializer`
    """

    class Meta:
        model = Collection
        fields = ('pk', 'name', 'url')

    url = serializers.SerializerMethodField('get_detail_data')

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Collection.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )


class ClassificationProjectCollectionNestedSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.ClassificationProjectCollection`
    that is used by :class:`ClassificationProjectSerializer`
    """
    class Meta:
        model = ClassificationProjectCollection
        fields = (
            'name', 'classifications_count', 'user_classifications_count'
        )

    name = serializers.ReadOnlyField(source='collection.collection.name')
    classifications_count = serializers.SerializerMethodField()
    user_classifications_count = serializers.SerializerMethodField()

    def get_classifications_count(self, item, *args, **kwargs):
        """Custom method for retrieving number of classifications connected to
        given classification project collection"""
        return item.classifications.count()

    def get_user_classifications_count(self, item):
        """Custom method for retrieving number of user classifications
        connected to given classification project collection"""
        user = self.context['request'].user
        return item.classifications.filter(
            user_classifications__owner__username=user
        ).count()


class UserClassificationSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.UserClassification`
    Serializer contains urls for details/delete user classification
    if user has enough permissions
    """

    class Meta:
        model = UserClassification
        fields = (
            'pk', 'owner', 'owner_profile', 'classification',
            'resource', 'collection', 'updated_at', 'approved',
            'created_at', 'static_attrs', 'dynamic_attrs',

            # data for action columns
            'detail_data', #'delete_data',
        )

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()
    resource = ResourceNestedSerializer(
        source='classification.resource'
    )
    collection = serializers.ReadOnlyField(source='classification.collection_id')
    approved = serializers.SerializerMethodField()
    dynamic_attrs = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    #delete_data = serializers.SerializerMethodField()

    def get_dynamic_attrs(self, item):
        """Custom method for retrieving dynamic attributes connected to given
        classification"""
        dynamic_attrs = item.dynamic_attrs.all()
        return_list = []
        for row in dynamic_attrs:
            return_list.append(row.attrs)
        return return_list

    def get_owner_profile(self, item):
        """Custom method for retrieving profile url"""
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return UserClassification.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    # def get_delete_data(self, item):
    #     """Custom method for retrieving delete url"""
    #     return UserClassification.objects.api_delete_context(
    #         item=item,
    #         user=self.context['request'].user
    #     )

    def get_approved(self, item):
        return item.classification.approved_source_id == item.pk


class ClassificationSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.Classification`
    Serializer contains urls for details/delete classification if user
    has enough permissions
    """

    class Meta:
        model = Classification
        fields = (
            'pk', 'resource', 'collection',
            'updated_at', 'static_attrs',
            'dynamic_attrs', 'status',
            # action columns
            'detail_data', 'delete_data',
            'classify_data',
            'update_data'
        )

    resource = ResourceNestedSerializer()
    collection = serializers.ReadOnlyField(source='collection_id')
    dynamic_attrs = serializers.SerializerMethodField()
    classify_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    update_data = serializers.SerializerMethodField()

    def get_dynamic_attrs(self, item):
        """Custom method for retrieving dynamic attributes connected to given
        classification"""
        dynamic_attrs = item.dynamic_attrs.all()
        return_list = []
        for row in dynamic_attrs:
            return_list.append(row.attrs)
        return return_list

    def get_classify_data(self, item):
        """Custom method for retrieving classification url"""
        return reverse(
            'media_classification:classify',
            kwargs={
                'pk': item.pk
            }
        )

    def get_detail_data(self, item):
        """Custom method for retrieving delete url"""
        return Resource.objects.api_detail_context(
            item=item.resource,
            user=self.context['request'].user
        )

    def get_update_data(self, item):
        """Custom method for retrieving delete url"""
        return Resource.objects.api_update_context(
            item=item.resource,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return reverse(
            'media_classification:classification_delete',
            kwargs={
                'pk': item.pk
            }
        )


class ClassificationMapSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.Classification`
    Serializer contains urls for details/delete classification if user
    has enough permissions
    """

    class Meta:
        model = Classification
        fields = (
            'pk', 'resource', 'static_attrs',
            'dynamic_attrs', 'classify_data',
            'project'
        )

    resource = ResourceNestedMapSerializer()
    dynamic_attrs = serializers.SerializerMethodField()
    classify_data = serializers.SerializerMethodField()

    def get_dynamic_attrs(self, item):
        """Custom method for retrieving dynamic attributes connected to given
        classification"""
        dynamic_attrs = item.dynamic_attrs.all()
        return_list = []
        for row in dynamic_attrs:
            return_list.append(row.attrs)
        return return_list

    def get_classify_data(self, item):
        """Custom method for retrieving classification url"""
        return Classification.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )


class ClassificatorSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.Classificator`
    Serializer contains urls for details/delete/update classificator if user
    has enough permissions
    """

    class Meta:
        model = Classificator
        fields = (
            'pk', 'name', 'owner', 'owner_profile', 'updated_date',
            'predefined_attrs', 'static_attrs_order',
            'custom_attrs', 'dynamic_attrs_order',
            'description', 'classification_projects',

            # data for action columns
            'update_data', 'detail_data', 'delete_data',
        )

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()
    classification_projects = serializers.ReadOnlyField(
        source='classification_projects.all.name'
    )

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
        return Classificator.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Classificator.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return Classificator.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )


class ClassificationProjectSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.ClassificationProject`
    Serializer contains urls for details/delete/update classification project
    if user has enough permissions
    """

    class Meta:
        model = ClassificationProject
        fields = (
            'pk', 'name', 'owner', 'owner_profile', 'classificator',
            'research_project', 'status', 'is_active', 'project_roles',
            'classificator_removed',
            # data for action columns
            'update_data', 'detail_data', 'delete_data',
        )

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()
    research_project = serializers.ReadOnlyField(source="research_project.name")
    status = serializers.ReadOnlyField(source='get_status_display')
    classificator_removed = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    project_roles = serializers.SerializerMethodField('get_roles')

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
        return ClassificationProject.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return ClassificationProject.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        """Custom method for retrieving delete url"""
        return ClassificationProject.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )

    def get_roles(self, item):
        """Custom method for retrieving list of roles connected to given
        classification project. Each role contain:

        * user (prettified version)
        * profile url
        * list of role names that user has in project
        """
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


class ClassificationProjectCollectionSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.ClassificationProjectCollection`
    Serializer contains urls for details/classify classification project
    collection if user has enough permissions
    """

    class Meta:
        model = ClassificationProjectCollection
        fields = (
            'pk', 'collection_pk', 'name', 'status',
            'is_active', 'deployments',

            'detail_data', 'classify_data',

            'approved_count', 'classified_count',
            'total_count'
        )

    name = serializers.ReadOnlyField(source='collection.collection.name')
    collection_pk = serializers.ReadOnlyField(source='collection.collection.pk')
    status = serializers.ReadOnlyField(source='collection.collection.status')
    deployments = serializers.SerializerMethodField()

    detail_data = serializers.SerializerMethodField()
    classify_data = serializers.SerializerMethodField()

    # basic stats
    approved_count = serializers.SerializerMethodField()
    classified_count = serializers.SerializerMethodField()
    total_count = serializers.SerializerMethodField()

    def get_deployments(self, item):
        """Custom method for retrieving list of deployments that are
        connected to resources within given classification project collection
        """
        deployments = [
            (k.deployment.pk, k.deployment.deployment_id) for k in \
            item.collection.collection.resources.prefetch_related(
                'deployment'
            ).all() if k.deployment
        ]
        deployments = list(set(deployments))
        deployments.sort(key=lambda x: x[1])
        return deployments

    def get_detail_data(self, item):
        """Custom method for retrieving detail url"""
        return Collection.objects.api_detail_context(
            item=item.collection.collection,
            user=self.context['request'].user
        )

    def get_classify_data(self, item):
        """Custom method for retrieving classify url"""
        return ClassificationProjectCollection.objects.api_classify_context(
            item=item,
            user=self.context['request'].user
        )

    def get_classified_count(self, item, *args, **kwargs):
        """Custom method for retrieving number of classifications connected to
        given classification project collection"""
        return item.classifications.filter(user_classifications__isnull=False).count()

    def get_approved_count(self, item, *args, **kwargs):
        """Custom method for retrieving number of approved classifications
        connected to given classification project collection"""
        return item.classifications.filter(status=True).count()

    def get_total_count(self, item):
        """Custom method for retrieving number of resources
        connected to given classification project collection"""
        return item.collection.collection.resources.count()


class SequenceReadSerializer(BasePKSerializer):
    """Serializer for
    :class:`apps.media_classification.models.Sequence`

    .. note::
        Within DRF sequences are readonly
    """

    class Meta:
        model = Sequence
        fields = (
            'pk', 'sequence_id', 'description', 'collection',
            'resources', 'created_at', 'owner'
        )

    owner = UserNestedSerializer(source='created_by')


class ClassificationResourceSerializer(BasePKSerializer):
    """Serializer for :class:`apps.storage.models.Resource`.

    This serializer has been defined because contains lots of heavy to retrieve
    information about classifications connected to resource, which aren't
    needed anywere else.
    """

    class Meta:
        model = Classification
        fields = (
            'pk', 'name', 'thumbnail_url',
            'url', 'mime', 'extra_url', 'extra_mime',
            'resource_type', 'date_recorded',
            'sequence', 'classification_data'
        )

    pk = serializers.ReadOnlyField(source='resource.pk')
    name = serializers.ReadOnlyField(source='resource.name')
    resource_type = serializers.ReadOnlyField(source='resource.resource_type')
    date_recorded = serializers.ReadOnlyField(source='resource.date_recorded_tz')
    url = serializers.ReadOnlyField(source='resource.get_url')
    mime = serializers.ReadOnlyField(source='resource.mime_type')
    extra_url = serializers.ReadOnlyField(source='resource.get_extra_url')
    extra_mime = serializers.ReadOnlyField(source='resource.extra_mime_type')
    thumbnail_url = serializers.ReadOnlyField(source='resource.get_thumbnail_url')
    sequence = serializers.ReadOnlyField(source='sequence.sequence_id')
    classification_data = serializers.SerializerMethodField()

    def get_classification_data(self, item):
        """Return information about classification connected to given
        resource that has been classified in given research project and
        belongs to given collection"""

        request = self.context['request']
        url = reverse(
            'media_classification:classify',
            kwargs={
                'pk': item.pk
            }
        )
        is_approved = item.is_approved
        is_new = not [
            k.owner == request.user for k in item.user_classifications.all()
        ]
        return {
            'is_approved': is_approved,
            'url': url,
            'is_new': is_new
        }
