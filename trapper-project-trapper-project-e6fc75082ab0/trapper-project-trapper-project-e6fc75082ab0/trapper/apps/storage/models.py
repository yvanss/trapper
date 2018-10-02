# -*- coding: utf-8 -*-

"""This module contains models and signals of the Storage application"""
from __future__ import unicode_literals

from django.utils.translation import ugettext as _

from mimetypes import guess_type
import itertools
import datetime

from django.conf import settings
from django.apps import apps
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Polygon
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from django.utils.timezone import now, get_current_timezone
from django.templatetags.tz import do_timezone

from taggit.models import TaggedItemBase
from taggit.managers import TaggableManager

from trapper.apps.geomap.models import Location
from trapper.apps.storage.taxonomy import (
    ResourceMimeType, ResourceStatus, ResourceType,
    CollectionStatus, CollectionMemberLevels
)
from trapper.middleware import get_current_user
from trapper.apps.messaging.models import (
    CollectionRequest, Message
)
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.accounts.models import UserTask
from trapper.apps.common.tools import datetime_aware
from trapper.apps.common.models import BaseAccessMember
from trapper.apps.storage.mixins import (
    AccessModelMixin, APIContextManagerMixin
)
from trapper.apps.common.fields import SafeTextField
from trapper.apps.common.utils.models import delete_old_file
from trapper.apps.storage.tasks import celery_update_thumbnails
from trapper.apps.storage.thumbnailer import Thumbnailer


class ResourceManager(APIContextManagerMixin, models.Manager):
    """The manager of the :class:`Resource` model.
    """

    url_update = 'storage:resource_update'
    url_detail = 'storage:resource_detail'
    url_delete = 'storage:resource_delete'
    use_for_related_fields = True

    def get_accessible(self, user=None, base_queryset=None, basic=False):
        """For given user it returns all accessible instances of the :class:`Resource`
        model. If user is not provided then currently logged in user is used.
        If there is no authenticated user then only public resources are
        returned.

        :param user: an instance of the :class:`django.contrib.auth.models.User` model
        :param base_queryset: a base queryset; by default it is :code:`Resource.objects.all()`.
        :param basic: a boolean value
        :return: resources queryset
        """

        public = ResourceStatus.PUBLIC
        public_collection = CollectionStatus.PUBLIC
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            return queryset.filter(status=public)

        levels = [
            CollectionMemberLevels.ACCESS,
            CollectionMemberLevels.ACCESS_REQUEST
        ]
        if basic:
            levels.append(
                CollectionMemberLevels.ACCESS_BASIC
            )

        collections = Collection.objects.get_accessible(
            user=user, role_levels=levels
        ).values_list('pk', flat=True)

        col_res = queryset.filter(
            collection__in=collections
        ).order_by('id').distinct('id').values_list('pk', flat=True)

        return queryset.filter(
            models.Q(status=public) |
            models.Q(owner=user) |
            models.Q(managers=user) |
            models.Q(pk__in=col_res)
        )
    
    
class TaggedResource(TaggedItemBase):
    content_object = models.ForeignKey('Resource')


class Resource(AccessModelMixin, models.Model):
    """Model describing the most basic entities used in other modules.
    Resource is usually a video or an image.
    In order to provide some robust playback features, it is possible to upload
    up to two separate resource files.

    Each resource can have its own share status: Private, Public or access on
    demand.

    Resources can be groupped into :class:`Collection`.
    """
    status_choices = ResourceStatus

    UPLOAD_DIR = 'protected/storage/resource/'
    THUMBNAIL_DIR = '{base}thumbnails/'.format(base=UPLOAD_DIR)
    PREVIEW_DIR = '{base}previews/'.format(base=UPLOAD_DIR)

    name = models.CharField(max_length=255)
    file = models.FileField(upload_to=UPLOAD_DIR)
    file_thumbnail = models.ImageField(
        upload_to=THUMBNAIL_DIR, blank=True, null=True, editable=False
    )
    file_preview = models.ImageField(
        upload_to=PREVIEW_DIR, blank=True, null=True, editable=False
    )
    extra_file = models.FileField(upload_to=UPLOAD_DIR, null=True, blank=True)

    mime_type = models.CharField(
        choices=ResourceMimeType.CHOICES, max_length=255,
        null=True, blank=True
    )
    extra_mime_type = models.CharField(
        choices=ResourceMimeType.CHOICES, max_length=255,
        null=True, blank=True
    )
    resource_type = models.CharField(
        choices=ResourceType.CHOICES, max_length=1, null=True, blank=True
    )
    date_uploaded = models.DateTimeField(null=True, blank=True, default=now)
    date_recorded = models.DateTimeField()
    deployment = models.ForeignKey(
        'geomap.Deployment', null=True, blank=True, related_name='resources',
        on_delete=models.PROTECT
    )
    status = models.CharField(
        choices=status_choices.CHOICES, max_length=8, default='Private'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='owned_resources'
    )
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='managed_resources'
    )
    description = SafeTextField(
        blank=True, null=True
    )
    inherit_prefix = models.BooleanField(
        default=False, verbose_name='Deployment ID prefix'
    )
    custom_prefix = models.CharField(max_length=255, blank=True, null=True)

    objects = ResourceManager()
    tags = TaggableManager(through=TaggedResource)


    class Meta:
        ordering = ('-date_recorded', )

    def can_view(self, user=None, basic=False):
        """
        """
        if self.status == 'Public':
            return True
        if self.collection_set.filter(
                status=CollectionStatus.PUBLIC
        ).count():
            return True
        if not user.is_authenticated():
            return False
        user = user or get_current_user()
        access_status = (
            self.owner_id == user.pk or user.pk in self.managers.values_list(
                'pk', flat=True
            )
        )
        if access_status:
            return True
        qs1 = user.collectionmember_set.values_list(
            'collection__pk', flat=True
        )
        if not basic:
            qs1 = qs1.exclude(
                level=CollectionMemberLevels.ACCESS_BASIC
            )
        qs2 = self.collection_set.values_list(
            'pk', flat=True
        ).exclude(owner=user,managers=user)
        return len(list(set(qs1) & set(qs2))) > 0

    def __unicode__(self):
        return u"{resource_type}: {name}".format(
            resource_type=self.get_resource_type_display(),
            name=self.name
        )

    @property
    def timezone(self):
        if self.deployment_id:
            return self.deployment.location.timezone
        else:
            return get_current_timezone()

    @property
    def date_recorded_tz(self):
        """Return local datetime according to location's timezone. If resource
        does not have an assigned location then default timezone is used."""
        return do_timezone(self.date_recorded, self.timezone)

    @property
    def prefixed_name(self):
        """Name of resource that support custom prefix and deployment_id (if
        inheriting is enabled)"""
        prefix_parts = []

        if self.custom_prefix:
            prefix_parts.append(self.custom_prefix)

        if self.inherit_prefix and self.deployment:
            deployment_id = self.deployment.deployment_id
            if deployment_id:
                prefix_parts.append(deployment_id)

        prefix_parts.append(self.name)
        return u"_".join(prefix_parts)

    @property
    def old_instance(self):
        """Get old instance of resource before it's saved"""
        if self.pk:
            return Resource.objects.get(pk=self.pk)

    def save(self, **kwargs):
        """Delete changed files if neccessary before save, and after save
        update collection bbox and period"""
        delete_old_file(self, 'file')
        delete_old_file(self, 'extra_file')

        old_instance = self.old_instance
        super(Resource, self).save(**kwargs)

        if old_instance:
            if self.deployment:
                if not old_instance.deployment or (
                        self.deployment.location != old_instance.deployment.location):
                    self.refresh_collection_bbox()
            if self.date_recorded != old_instance.date_recorded:
                self.refresh_collection_period()

    def refresh_collection_bbox(self):
        """Refresh all connected collections bbox for given resource"""
        for collection in self.collection_set.all():
            collection.refresh_bbox()

    def refresh_collection_period(self):
        """Refresh all connected collections periods for given resource"""
        for collection in self.collection_set.all():
            collection.refresh_period()

    @property
    def is_public(self):
        """Return True if resource is publicly available"""
        return self.status == ResourceStatus.PUBLIC

    def get_absolute_url(self):
        """Get the absolute url for an instance of this model."""
        return reverse('storage:resource_detail', kwargs={'pk': self.pk})

    def can_remove_comment(self, user=None):
        """Method used by trapper.apps.comments application
        to determine when comments related to Resource can be removed"""
        user = user or get_current_user()
        return self.owner == user

    def generate_thumbnails(self):
        """When resource is created, thumbnail is generated
        For small resources thumbnail is generated without celery.
        For larger ones, if celery processing is enabled - thumbnail
        is generated as celery task"""
        if self.resource_type in ResourceType.THUMBNAIL_TYPES:
            if (
                settings.CELERY_ENABLED and
                self.file.size > settings.CELERY_MIN_IMAGE_SIZE
            ):
                task = celery_update_thumbnails.delay(
                    resources=[self,]
                )
                user_task = UserTask(
                    user=self.owner,
                    task_id=task.task_id
                )
                user_task.save()
            else:
                Thumbnailer(self).create()

    def update_metadata(self, commit=False):
        """Updates the internal metadata about the resource.

        :param commit: States whether to perform self.save() at the end of
            this method
        """

        self.update_mimetype(commit=False)
        self.update_resource_type(commit=False)

        if commit:
            self.save()

    def update_resource_type(self, commit=False):
        """Sets resource_type based on mime_type.

        :param commit: States whether to perform self.save() at the end of
            this method
        """

        if not self.mime_type:
            self.update_mimetype(commit=False)

        if self.mime_type.startswith('audio'):
            self.resource_type = ResourceType.TYPE_AUDIO
        elif self.mime_type.startswith('video'):
            self.resource_type = ResourceType.TYPE_VIDEO
        elif self.mime_type.startswith('image'):
            self.resource_type = ResourceType.TYPE_IMAGE

        if self.extra_file and not self.extra_mime_type:
            self.update_extra_mimetype(commit=False)

        if commit:
            self.save()

    def update_mimetype(self, commit=False):
        """Sets the mime_type for the resource.
        This is obtained by trying to *guess* the mime type based on the
        resource file.

        :param commit: States whether to perform self.save() at the end of
            this method
        """
        self.mime_type = guess_type(self.file.path)[0]
        if self.extra_file:
            self.extra_mime_type = guess_type(self.extra_file.path)[0]

        if commit:
            self.save()

    def update_extra_mimetype(self, commit=False):
        """Sets the extra mime_type for the extra resource file.
        This is obtained by trying to *guess* the mime type based on the
        resource file.

        :param commit: States whether to perform self.save() at the end of
            this method
        """
        self.extra_mime_type = guess_type(self.extra_file.path)[0]

        if commit:
            self.save()

    def get_icon_class(self):
        return 'add_icon_%s' % self.get_resource_type_display().lower()

    def get_url(self):
        field = 'file'
        if self.resource_type == ResourceType.TYPE_IMAGE:
            field = 'pfile'
        return reverse(
            'storage:resource_sendfile_media',
            kwargs={'pk': self.pk, 'field': field}
        )

    def get_url_original(self):
        return reverse(
            'storage:resource_sendfile_media',
            kwargs={'pk': self.pk, 'field': 'file'}
        )

    def get_thumbnail_url(self):
        """Return url of thumbnail based on resource type"""
        base_url = "/static/trapper_storage/img/{name}"
        url = reverse(
            'storage:resource_sendfile_media',
            kwargs={'pk': self.pk, 'field': 'tfile'}
        )

        thumbnail = base_url.format(name="no_thumb_100x100.jpg")
        if self.resource_type == ResourceType.TYPE_IMAGE:
            if self.file_thumbnail:
                thumbnail = url
            else:
                thumbnail = base_url.format(name="no_thumb_image_100x100.jpg")
        elif self.resource_type == ResourceType.TYPE_AUDIO:
            thumbnail = base_url.format(name="no_thumb_audio_100x100.jpg")
        elif self.resource_type == ResourceType.TYPE_VIDEO:
            if self.file_thumbnail:
                thumbnail = url
            else:
                thumbnail = base_url.format(name="no_thumb_video_100x100.jpg")
        return thumbnail

    def get_extra_url(self):
        return reverse(
            'storage:resource_sendfile_media',
            kwargs={'pk': self.pk, 'field': 'efile'}
        )

    def check_date_recorded(self):
        """Determines if a date when a resource was recorded falls within
        a deployment period. If resource has no deployment assigned returns
        True.
        """
        if not self.deployment:
            return True
        if self.deployment.start_date and self.deployment.end_date:
            return self.date_recorded > self.deployment.start_date\
                and self.date_recorded < self.deployment.end_date
        else:
            # as it is impossible to test it returns True to not display
            # a warning message
            return True


class ResourceUserRate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    resource = models.ForeignKey(Resource, related_name='user_ratings')
    rating = models.DecimalField(max_digits=6, decimal_places=1, default=0)


class ResourceAverageRate(models.Model):
    resource = models.OneToOneField(Resource, related_name='rating')
    average = models.DecimalField(max_digits=6, decimal_places=1, default=0)


class CollectionManager(APIContextManagerMixin, gis_models.Manager):
    """Manager for :class:`Collection` model.

    This manager contains additional logic used byy DRF serializers like
    details/update/delete urls
    """
    url_update = 'storage:collection_update'
    url_detail = 'storage:collection_detail'
    url_delete = 'storage:collection_delete'

    def get_accessible(self, user=None, base_queryset=None, role_levels=None):
        """Return all :class:`Collection` instances that given user
        has access to. If user is not defined, then currently logged in user
        is used.
        If there is no authenticated user then only
        :class:`apps.storage.taxonomy.CollectionStatus.PUBLIC` collections are
        returned

        :param user: if not none then that user will be used to filter
            accessible collections. If passed user not logged in,
            then collections are limited to PUBLIC only. If user is None
            then currently logged in user is used.
        :param base_queryset: queryset used to limit checked collections.
            by default it's all collections.
        :param role_levels: list of :class:`CollectionMemberLevels` levels
            that user is required to have to access collections

        :return: collections queryset
        """
        user = user or get_current_user()
        public = CollectionStatus.PUBLIC

        if not role_levels:
            role_levels = (
                CollectionMemberLevels.ACCESS,
                CollectionMemberLevels.ACCESS_REQUEST
            )

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            return queryset.filter(status=public)

        colmem = CollectionMember.objects.filter(
            user=user, level__in=role_levels
        ).values_list('pk', flat=True)
        
        colmem_col = queryset.filter(
            collectionmember__in=colmem
        ).order_by('id').distinct('id').values_list('pk', flat=True)

        return queryset.filter(
            models.Q(owner=user) |
            models.Q(managers=user) |
            models.Q(status=public) |
            models.Q(pk__in=colmem_col)
        )

    def get_ondemand(self, user, base_queryset=None):
        """
        """
        user = user or get_current_user()
        if not user.is_authenticated():
            return Collection.objects.none()

        ondemand = CollectionStatus.ON_DEMAND

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        return queryset.filter(status=ondemand).exclude(
            models.Q(owner=user) |
            models.Q(managers=user) |
            (
                models.Q(collectionmember__user=user) &
                models.Q(
                    collectionmember__level=1
                )
            )
        ).distinct()

    def get_editable(self, user=None, base_queryset=None):
        """Get queryset with collections that can be updated by given user

        :param user: if not none then that user will be used to filter
            accessible collections. If passed user not logged in,
            then queryset is empty. If user is None
            then currently logged in user is used.
        :param base_queryset: queryset used to limit checked collections.
            by default it's all collections.
        """
        user = user or get_current_user()

        if not user.is_authenticated():
            return Collection.objects.none()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        level = CollectionMemberLevels.UPDATE
        return queryset.filter(
            models.Q(owner=user) |
            models.Q(managers=user) |
            (
                models.Q(members=user) &
                models.Q(members__collectionmember__level=level)
            )
        ).distinct()

    def get_removable(self, user=None, base_queryset=None):
        """Get queryset with collections that can be removed by given user

        :param user: if not none then that user will be used to filter
            accessible collections. If passed user not logged in,
            then queryset is empty. If user is None
            then currently logged in user is used.
        :param base_queryset: queryset used to limit checked collections.
            by default it's all collections.
        """
        user = user or get_current_user()

        if not user.is_authenticated():
            return Collection.objects.none()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        level = CollectionMemberLevels.DELETE
        return queryset.filter(
            models.Q(owner=user) |
            models.Q(managers=user) |
            (
                models.Q(members=user) &
                models.Q(members__collectionmember__level=level)
            )
        ).distinct()

    def api_ask_access_context(self, item, user):
        """Method used to determine if other users can ask for permissions
        Requests for permissions are allowed only for On demand collections and
        asking is allowed once per 24h
        """
        is_public = item.is_public
        context = {
            'is_public': is_public
        }
        if not is_public:
            if item.can_view(user=user):
                context['already_approved'] = True
            else:
                if user.is_authenticated():
                    already_approved = user.my_collection_requests.filter(
                        collections__pk=item.pk,
                        resolved_at__isnull=False,
                        is_approved=True
                    ).exists()
                    if already_approved:
                        context['already_approved'] = already_approved
                    else:
                        url = reverse(
                            'storage:collection_request', args=(item.pk,)
                        )
                        try:
                            collection_request = \
                                user.my_collection_requests.filter(
                                    collections__pk=item.pk,
                                    resolved_at__isnull=True
                                ).latest('added_at')
                        except CollectionRequest.DoesNotExist:
                            request_status = None
                            context['url'] = url
                        else:
                            # If request is older than time defined in
                            # settings, then it doesn't matter
                            diff = (
                                datetime_aware() - collection_request.added_at
                            )
                            if diff.seconds > settings.REQUEST_FLOOD_DELAY:
                                context['url'] = url
                                request_status = None
                            else:
                                request_status = collection_request.added_at
                        context['delay'] = settings.REQUEST_FLOOD_DELAY / 3600
                        context['status'] = request_status
        return context


class Collection(AccessModelMixin, models.Model):
    """Base container for grouping :class:`storage:Resource` model instances.
    Collections are used in other modules such as research projects or
    classification projects"""

    member_levels = CollectionMemberLevels
    status_choices = CollectionStatus

    name = models.CharField(max_length=255)
    description = SafeTextField(max_length=2000, null=True, blank=True)
    resources = models.ManyToManyField(Resource)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='owned_collections')
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='managed_collections',
        help_text='Select your managers.'
    )
    status = models.CharField(
        choices=CollectionStatus.CHOICES, max_length=8, default='Private'
    )
    date_created = models.DateTimeField(editable=False, auto_now_add=True)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through='CollectionMember', blank=True
    )
    bbox = gis_models.PolygonField(blank=True, null=True)
    period_begin = models.DateTimeField(blank=True, null=True)
    period_end = models.DateTimeField(blank=True, null=True)

    objects = CollectionManager()

    class Meta:
        ordering = ['name',]

    @property
    def is_public(self):
        """Return True if resource is publicly available"""
        return self.status == ResourceStatus.PUBLIC

    def __unicode__(self):
        return unicode("%s | %s" % (self.name, self.owner.username))

    def get_absolute_url(self):
        """Get the absolute url for an instance of this model."""
        return reverse('storage:collection_detail', kwargs={'pk': self.pk})

    def can_add_to_research_project(self, user=None):
        """Check if collection can be added to research project"""
        user = user or get_current_user()
        return user == self.owner or user in self.managers.all()

    def is_used(
            self, user=None, rproject=None, cproject=None
    ):
        """ The helper method to check if user should still have access to
        this collection.
        """
        # get models
        research_project = apps.get_model('research', 'ResearchProject')
        classification_project = apps.get_model(
            'media_classification', 'ClassificationProject'
        )
        user = user or get_current_user()
        # step 1
        rprojects = research_project.objects.filter(
            collections=self, project_roles__user=user
        ).distinct()
        if rproject:
            return rprojects.exists()
        # step 2
        cprojects = classification_project.objects.filter(
            collections__collection=self, classification_project_roles__user=user
        ).distinct()
        if cproject:
            return cprojects.exists()
        return rprojects.exists() or cprojects.exists()

    def delete(self, **kwargs):
        """Send notification before deleting objects"""
        delete_collection_notification(instance=self)
        return super(Collection, self).delete(**kwargs)

    def refresh_bbox(self):
        """Recalculate border polygon containing all coordinates from
        resources assigned to collection"""
        locations = Location.objects.filter(
            pk__in=self.resources.filter(
                deployment__location__isnull=False
            ).values_list('deployment__location__pk', flat=True)
        )
        if locations.count() > 1:
            extant = locations.extent()
            point1_x, point1_y, point2_x, point2_y = extant

            points = [
                (point1_x, point1_y),
                (point2_x, point1_y),
                (point2_x, point2_y),
                (point1_x, point2_y),
                (point1_x, point1_y),
            ]
            polygon = Polygon(points).buffer(1).envelope
            self.bbox = polygon
        else:
            self.bbox = None
            self.save()

    @property
    def period(self):
        """Return tuple with period dates"""
        return self.period_begin, self.period_ends

    def refresh_period(self):
        """Recalculate period as oldest and latest date_recorded
        from all resources connected to collection"""
        period = self.resources.aggregate(
            begin=models.Min('date_recorded'),
            end=models.Max('date_recorded')
        )
        self.period_begin = period['begin']
        self.period_end = period['end']
        self.save()

    def get_orphaned_resources(self, user=None):
        """
        """
        user = user or get_current_user()
        if self.can_update(user=user):
            all_res = self.resources.values_list('pk', flat=True)
            accessible = self.resources.get_accessible(
                user=user
            ).values_list('pk', flat=True)
            diff_pks = list(set(all_res).difference(set(accessible)))
            return diff_pks
        else:
            return None


class CollectionMember(BaseAccessMember):
    """Class used to define user access levels for :class:`Collection`"""
    collection = models.ForeignKey(Collection)
    level = models.IntegerField(choices=CollectionMemberLevels.CHOICES)


@receiver(post_delete, sender=Resource)
def delete_files(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(False)
    if instance.file_thumbnail:
        instance.file_thumbnail.delete(False)
    if instance.extra_file:
        instance.extra_file.delete(False)
    if instance.file_preview:
        instance.file_preview.delete(False)


@receiver(post_save, sender=ResourceUserRate)
def update_resource_rating(sender, instance, **kwargs):
    """
    Signal used to update the average rating of given resource
    """
    obj, created = ResourceAverageRate.objects.get_or_create(
        resource=instance.resource
    )
    # Calculate the average rating
    rating_avg = ResourceUserRate.objects.filter(
        resource=instance.resource
    ).aggregate(models.Avg('rating'))
    if rating_avg.get('rating__avg'):
        obj.average = rating_avg['rating__avg']
    else:
        obj.average = 0
    obj.save()


@receiver(m2m_changed, sender=Collection.resources.through)
def update_collection_data(sender, instance, action, **kwargs):
    """
    Signal used to update gis data in collection

    :param sender: :class:`Collection.resources.through`
    :param instance: :class:`Collection`
    :param action: pre_clear or post_add are used
    :param kwargs: additional arguments sent by signal
    """
    if action in ['post_add', 'post_remove', 'post_clear']:
        instance.refresh_bbox()
        instance.refresh_period()


@receiver(m2m_changed, sender=Collection.resources.through)
def rebuild_cp_collections(sender, instance, action, **kwargs):
    """
    Signal used to update classification project collections i.e.
    to rebuild base classifications objects

    :param sender: :class:`Collection.resources.through`
    :param instance: :class:`Collection`
    :param action: pre_clear or post_add are used
    :param kwargs: additional arguments sent by signal
    """
    from trapper.apps.media_classification.models import ClassificationProjectCollection
    if action in ['post_add', 'post_remove', 'post_clear']:
        cp_collections = ClassificationProjectCollection.objects.filter(
            collection__collection=instance
        )
        for cp_collection in cp_collections:
            cp_collection.rebuild_classifications()


def collections_access_grant(
        collections, users,
        level=CollectionMemberLevels.ACCESS_BASIC
):
    """
    Method used to grant an access to specified collections.

    Add specified permission level :class:`CollectionMemberLevels`
    to all specified users for all specified collections.

    :param users: iterable of :class:`auth.User` instances
    :param collections: iterable of :class:`Collection`
    :return: None
    """
    for user, collection in itertools.product(users, collections):
        if not collection.owner_id == user.pk and \
           not user.pk in collection.managers.values_list(
               'pk', flat=True
           ) and not collection.is_public:
            CollectionMember.objects.get_or_create(
                collection=collection,
                user=user,
                level=level
            )


def collections_access_revoke(
        collection_pks, user_pks,
        rproject=None, cproject=None,
        level=CollectionMemberLevels.ACCESS_BASIC
):
    """
    Method used to revoke an access to specified collections.

    Remove all entries with specified level :class:`CollectionMemberLevels`
    or for all given resources and all given users.

    :param users: iterable of :class:`auth.User` instances
    :param collections: iterable of :class:`Collection`
    :return: None
    """
    queryset = CollectionMember.objects.filter(
        collection__pk__in=collection_pks,
        user__pk__in=user_pks, level=level
    ).prefetch_related('collection', 'user')

    for m in queryset:
        user = m.user
        collection = m.collection
        params = {'user': user}
        if rproject:
            params.update({'rproject': rproject})
        if cproject:
            params.update({'cproject': cproject})
        if collection.is_used(**params):
            queryset = queryset.exclude(
                collection=collection, user=user,
            )
    queryset.delete()


def delete_collection_notification(instance):
    """
    Messages sent when collection is deleted to:
    * owner
    * all managers
    * owners of collections
    * all users that have access to resource
    """
    user = get_current_user()
    recipients = set()
    # Owner
    recipients.add(instance.owner)
    # managers
    recipients.update(instance.managers.all())
    # people with access
    recipients.update(
        CollectionMember.objects.filter(
            collection=instance,
            level=CollectionMemberLevels.ACCESS
        )
    )

    for recipient in recipients:
        if user and recipient:
            Message.objects.create(
                subject=u"Collection: {name} has been deleted".format(name=instance.name),
                text=u"Collection: {name} has been deleted".format(name=instance.name),
                user_from=user,
                user_to=recipient,
                date_sent=now(),
                message_type=MessageType.RESOURCE_DELETED
            )
