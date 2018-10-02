# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import operator

from django.contrib.gis.db import models
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.apps import apps 
from django.conf import settings
from django.templatetags.tz import do_timezone

from leaflet_storage.models import Map
from pygeocoder import Geocoder, GeocoderError
from timezone_field import TimeZoneField
from taggit.managers import TaggableManager

from trapper.middleware import get_current_user
from trapper.apps.common.fields import SafeTextField
from trapper.apps.storage.mixins import APIContextManagerMixin
from trapper.apps.geomap.taxonomy import DeploymentViewQuality


class MapManagerUtils(object):

    @classmethod
    def get_accessible(cls, user=None):
        user = user or get_current_user()
        if user.is_authenticated():
            queryset = Map.objects.filter(
                models.Q(owner=user) |
                models.Q(editors=user)
            )
        else:
            queryset = Map.objects.filter(
                share_status=Map.PUBLIC
            )
        return queryset


class LocationManager(models.GeoManager):
    url_update = 'geomap:map_view'
    url_detail = 'geomap:location_detail'
    url_delete = 'geomap:location_delete'

    def get_available(
            self, user=None, base_queryset=None,
            public=True, editable_only=False
    ):

        user = user or get_current_user()
        resource_model = apps.get_model('storage', 'Resource')

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        params = {}
        if public is not None:
            params['is_public'] = bool(public)

        if user.is_authenticated():
            params['owner'] = user
            params['managers'] = user

        # if user has access to a resource (e.g. through a project role)
        # it should also have acccess to a resource's location

        if not editable_only:
            resources = resource_model.objects.get_accessible(
                user=user, basic=True
            )
            res_loc = queryset.filter(
                deployments__resources__in=resources
            ).order_by('id').distinct('id')
            params['pk__in'] = res_loc

        filter_params = reduce(
            operator.or_, map(models.Q, params.items())
        )
        return queryset.filter(filter_params)

    def api_update_context(self, item, user):
        context = None
        if item.can_update(user):
            context = u"{url}?locations={pk}&edit=true".format(
                url=reverse(self.url_update),
                pk=item.pk
            )
        return context

    def api_detail_context(self, item, user):
        context = None
        #if item.can_view(user):
        context = reverse(self.url_detail, kwargs={'pk': item.pk})
        return context

    def api_delete_context(self, item, user):
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class Location(models.Model):

    """Single location (Point) on map.
    This model is often referred by other models for establishing a
    spatial context.
    """

    location_id = models.CharField(max_length=100)
    name = models.CharField(max_length=255, null=True, blank=True)
    date_created = models.DateTimeField(blank=True, editable=False)
    description = models.TextField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    coordinates = models.PointField(srid=4326)
    timezone = TimeZoneField(default=timezone.get_default_timezone_name())
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_locations')
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='managed_locations', blank=True
    )
    country = models.CharField(
        max_length=100, blank=True, null=True, editable=False
    )
    state = models.CharField(
        max_length=100, blank=True, null=True, editable=False
    )
    county = models.CharField(
        max_length=100, blank=True, null=True, editable=False
    )
    city = models.CharField(
        max_length=100, blank=True, null=True, editable=False
    )
    research_project = models.ForeignKey(
        'research.ResearchProject', blank=True, null=True
    )

    objects = LocationManager()

    class Meta:
        unique_together = ['research_project', 'location_id']

    @property
    def get_x(self):
        return self.coordinates.x

    @property
    def get_y(self):
        return self.coordinates.y

    @property
    def owner_name(self):
        return self.owner.username

    @property
    def latlng(self):
        return "{}, {}".format(self.coordinates.y, self.coordinates.x)

    def can_view(self, user=None):
        """Determines whether user can view the location.
        :param user: user for which the test is made
        :type user: :py:class:`django.contrib.auth.User`
        :return: True if user can see the location, False otherwise
        :rtype: bool
        """
        user = user or get_current_user()

        return (
            self.is_public or user == self.owner or user in self.managers.all()
        )

    def can_update(self, user=None):
        user = user or get_current_user()
        return (
            user == self.owner or user in self.managers.all()
        )

    def can_delete(self, user=None):
        user = user or get_current_user()
        return user == self.owner

    def save(self, **kwargs):
        if self.date_created is None:
            self.date_created = timezone.now()
        old_instance = None

        if self.pk:
            old_instance = Location.objects.get(pk=self.pk)

        if (
            settings.REVERSE_GEOCODING and
            (
                not self.pk or
                (old_instance and self.coordinates != old_instance.coordinates)
            )
        ):
            self.reverse_geocoding()

        super(Location, self).save(**kwargs)

        if old_instance and self.coordinates != old_instance.coordinates:
            for deployment in self.deployments.all():
                for resource in deployment.resources.all():
                    resource.refresh_collection_bbox()

    def reverse_geocoding(self, set_fields=True, return_data=False):
        """ using pygeocoder: http://code.xster.net/pygeocoder/wiki/Home
        update fields:

        .. code-block::
            * city
            * county
            * state
            * country

        In case of `GeocoderException` required fields will be set to empty.
        """
        parsed_data = {
            'city': '',
            'county': '',
            'state': '',
            'country': '',
            }

        try:
            results = Geocoder.reverse_geocode(
                self.coordinates.y, self.coordinates.x
            )
        except GeocoderError:
            pass
        else:

            for k in results.data[0]['address_components']:
                if 'locality' in k['types']:
                    parsed_data['city'] = k['long_name']
                if 'administrative_area_level_2' in k['types']:
                    parsed_data['county'] = k['long_name']
                if 'administrative_area_level_1' in k['types']:
                    parsed_data['state'] = k['long_name']
                if 'country' in k['types']:
                    parsed_data['country'] = k['long_name']

            if set_fields:
                for key, value in parsed_data.items():
                    setattr(self, key, value)
            if return_data:
                return parsed_data

    def __unicode__(self):
        return unicode("Location: %s" % (self.location_id, ))

    class Meta:
        ordering = ['-pk']


class DeploymentManager(APIContextManagerMixin, models.Manager):
    """Manager for :class:`Deployment` model.

    This manager contains additional logic used by DRF serializers like
    details/update/delete urls
    """
    url_update = 'geomap:deployment_update'
    url_detail = 'geomap:deployment_detail'
    url_delete = 'geomap:deployment_delete'

    def get_accessible(self, user=None, base_queryset=None, editable_only=False):
        """Return all :class:`Deployment` instances that given user
        has access to. If user is not defined, then currently logged in user
        is used.

        :param user: if not none then that user will be used to filter
            accessible deployments. If user is None
            then currently logged in user is used.
        :param base_queryset: queryset used to limit checked deployments.
            by default it's all deployments.

        :return: deployments queryset
        """
        resource_model = apps.get_model('storage', 'Resource')
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            return queryset.none()

        params = {}

        if user.is_authenticated():
            params['owner'] = user
            params['managers'] = user

        # # if user has access to a resource (e.g. through a project role)
        # # it should also have acccess to data on related deployment

        if not editable_only:
            resources = resource_model.objects.get_accessible(
                user=user, basic=True
            )
            res_dep = queryset.filter(
                resources__in=resources
            ).order_by('id').distinct('id')
            params['pk__in'] = res_dep

        filter_params = reduce(
            operator.or_, map(models.Q, params.items())
        )
        return queryset.filter(filter_params)

    def api_update_context(self, item, user):
        context = None
        if item.can_update(user):
            context = reverse(self.url_update, kwargs={'pk': item.pk})
        return context

    def api_detail_context(self, item, user):
        context = None
        #if item.can_view(user):
        context = reverse(self.url_detail, kwargs={'pk': item.pk})
        return context

    def api_delete_context(self, item, user):
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class Deployment(models.Model):

    """Deployment model links Resource with Location.
    This model enriches a spatial context given by Location.
    The extra information includes observation period and sensor
    (e.g. camera trap or ordinary camera) used to record a given
    set of resources.
    """

    deployment_code = models.CharField(max_length=50)
    location = models.ForeignKey(Location, related_name='deployments')
    #sensor = models.ForeignKey(Sensor)
    deployment_id = models.CharField(
        blank=True, editable=False, max_length=100
    )
    start_date = models.DateTimeField(blank=True, null=True)
    end_date = models.DateTimeField(blank=True, null=True)
    correct_setup = models.BooleanField(default=True)
    correct_tstamp = models.BooleanField(default=True)
    view_quality = models.CharField(
        choices=DeploymentViewQuality.CHOICES, max_length=255,
        null=True, blank=True, default='Good'
    )
    research_project = models.ForeignKey(
        'research.ResearchProject', blank=True, null=True
    )
    date_created = models.DateTimeField(blank=True, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_deployments')
    comments = SafeTextField(blank=True, null=True)
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name='managed_deployments', blank=True
    )

    tags = TaggableManager()
    objects = DeploymentManager()

    class Meta:
        ordering = ['deployment_id',]

    @property
    def timezone(self):
        return self.location.timezone

    @property
    def start_date_tz(self):
        """Return local datetime according to location's timezone."""
        return do_timezone(self.start_date, self.timezone)

    @property
    def end_date_tz(self):
        """Return local datetime according to location's timezone."""
        return do_timezone(self.end_date, self.timezone)

    def get_absolute_url(self):
        """Get the absolute url for an instance of this model."""
        return reverse('geomap:deployment_detail', kwargs={'pk': self.pk})

    def update_deployment_id(self, save=True):
        self.deployment_id = "-".join(
            [self.deployment_code, self.location.location_id]
        )
        if save:
            self.save()

    def save(self, **kwargs):
        if self.date_created is None:
            self.date_created = timezone.now()
        self.update_deployment_id(save=False)
        super(Deployment, self).save(**kwargs)

    def can_view(self, user=None):
        """Determines whether user can view the deployment.
        :param user: user for which the test is made
        :type user: :py:class:`django.contrib.auth.User`
        :return: True if user can see the deployment, False otherwise
        :rtype: bool
        """
        user = user or get_current_user()
        if user == self.owner or user in self.managers.all():
            return True
        if self.resources.get_accessible(user=user, basic=True).count():
            return True
        return False

    def can_update(self, user=None):
        user = user or get_current_user()
        return (
            user == self.owner or user in self.managers.all()
        )

    def can_delete(self, user=None):
        """Deployment can not be deleted when there are resources that
        refer to it through a protected foreign key.
        """
        return self.can_update()

    def __unicode__(self):
        return unicode(self.deployment_id)
