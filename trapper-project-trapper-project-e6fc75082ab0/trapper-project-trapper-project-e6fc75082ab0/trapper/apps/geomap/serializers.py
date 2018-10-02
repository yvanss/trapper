# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse

from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from leaflet_storage.models import Map

from trapper.apps.geomap.models import Location, Deployment
from trapper.apps.common.serializers import BasePKSerializer, PrettyUserField


class LocationSerializer(BasePKSerializer):

    class Meta:
        model = Location
        fields = (
            'pk', 'name', 'date_created', 'description', 'location_id',
            'is_public', 'coordinates', 'owner', 'owner_profile',
            'city', 'county', 'state', 'country', 'research_project',
            'timezone',

            # data for action columns
            'update_data', 'delete_data',
        )

    owner = PrettyUserField()
    research_project = serializers.ReadOnlyField(
        source='research_project.acronym'
    )
    timezone = serializers.ReadOnlyField(
        source='timezone.__str__'
    )
    owner_profile = serializers.SerializerMethodField()
    update_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()
    coordinates = serializers.SerializerMethodField()

    def get_coordinates(self, item):
        return '{}, {}'.format(
            round(item.get_x, 5),
            round(item.get_y, 5)
        )

    def get_owner_profile(self, item):
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_update_data(self, item):
        return Location.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        return Location.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )


class LocationGeoSerializer(GeoFeatureModelSerializer):
    """ A class to serialize locations as GeoJSON compatible data """

    class Meta:
        model = Location
        geo_field = 'coordinates'
        fields = (
            'pk', 'location_id', 'name',
        )


class DeploymentSerializer(BasePKSerializer):

    class Meta:
        model = Deployment
        fields = (
            'pk', 'deployment_code', 'deployment_id', 'location',
            'location_id', 'start_date', 'end_date', 'owner',
            'owner_profile', 'research_project', 'tags',
            'correct_setup', 'correct_tstamp',

            # data for action columns
            'detail_data', 'update_data', 'delete_data'
        )

    owner = PrettyUserField()
    location_id = serializers.ReadOnlyField(source='location.location_id')
    start_date = serializers.ReadOnlyField(source='start_date_tz')
    end_date = serializers.ReadOnlyField(source='end_date_tz')
    research_project = serializers.ReadOnlyField(source='research_project.acronym')
    tags = serializers.SerializerMethodField()
    owner_profile = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()
    update_data = serializers.SerializerMethodField()
    delete_data = serializers.SerializerMethodField()

    def get_owner_profile(self, item):
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )

    def get_tags(self, obj):
        """Custom method for retrieving depoyment tags"""
        return [k.name for k in obj.tags.all()]

    def get_detail_data(self, item):
        return Deployment.objects.api_detail_context(
            item=item,
            user=self.context['request'].user
        )

    def get_update_data(self, item):
        return Deployment.objects.api_update_context(
            item=item,
            user=self.context['request'].user
        )

    def get_delete_data(self, item):
        return Deployment.objects.api_delete_context(
            item=item,
            user=self.context['request'].user
        )


class MapSerializer(BasePKSerializer):

    class Meta:
        model = Map
        fields = (
            'pk', 'slug', 'description', 'center', 'zoom', 'locate',
            'licence', 'modified_at', 'tilelayer', 'owner', 'owner_profile',
            'edit_status', 'share_status', 'settings',

            'delete_data', 'detail_data',

        )

    owner = PrettyUserField()
    owner_profile = serializers.SerializerMethodField()
    licence = serializers.ReadOnlyField(source='licence.name')
    edit_status = serializers.ReadOnlyField(source='get_edit_status_display')
    share_status = serializers.ReadOnlyField(source='get_share_status_display')
    tilelayer = serializers.ReadOnlyField(source='tilelayer.url_template')

    delete_data = serializers.SerializerMethodField()
    detail_data = serializers.SerializerMethodField()

    def get_delete_data(self, item):
        user = self.context['request'].user
        if item.owner == user:
            return reverse('geomap:map_delete', kwargs={'pk': item.pk})

    def get_detail_data(self, item):
        user = self.context['request'].user
        if item.owner == user or user in item.editors.all():
            return reverse(
                'geomap:map',
                kwargs={'pk': item.pk, 'slug': item.slug}
            )

    def get_owner_profile(self, item):
        return reverse(
            'accounts:show_profile', kwargs={'username': item.owner.username}
        )


class LocationTableSerializer(serializers.ModelSerializer):
    """
    """

    class Meta:
        model = Location
        fields = [
            'id', 'location_id', 'X', 'Y', 'name', 'description',
            'country', 'state', 'county', 'city', 'timezone',
            'research_project'
        ]

    X = serializers.SerializerMethodField()
    Y = serializers.SerializerMethodField()
    research_project = serializers.ReadOnlyField(
        source='research_project_id'
    )
    timezone = serializers.ReadOnlyField(
        source='timezone.__str__'
    )


    def get_X(self, item):
        return round(item.get_x, 5)

    def get_Y(self, item):
        return round(item.get_y, 5)


class DeploymentTableSerializer(serializers.ModelSerializer):
    """
    """

    class Meta:
        model = Deployment
        fields = [
            'id', 'deployment_id', 'deployment_code',
            'deployment_start', 'deployment_end',
            'location_id', 'location_X', 'location_Y',
            'location_tz', 'research_project',
            'correct_setup', 'correct_tstamp', 
            'view_quality', 'comments',
        ]

    deployment_start = serializers.ReadOnlyField(
        source='start_date_tz'
    )
    deployment_end = serializers.ReadOnlyField(
        source='end_date_tz'
    )
    location_id = serializers.ReadOnlyField(
        source='location.location_id'
    )
    location_X = serializers.SerializerMethodField()
    location_Y = serializers.SerializerMethodField()
    location_tz = serializers.ReadOnlyField(
        source='location.timezone.zone'
    )
    research_project = serializers.ReadOnlyField(
        source='research_project_id'
    )

    def get_location_X(self, item):
        return round(item.location.get_x, 5)

    def get_location_Y(self, item):
        return round(item.location.get_y, 5)


