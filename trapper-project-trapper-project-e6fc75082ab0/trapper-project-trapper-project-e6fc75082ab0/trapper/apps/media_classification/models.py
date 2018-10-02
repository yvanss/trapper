# -*- coding: utf-8 -*-
"""Module contains models and signals for media classification application and
permissions related to it"""
from __future__ import unicode_literals

import json
import operator

from collections import OrderedDict

from django_hstore import hstore

from django.db import models
from django.core.urlresolvers import reverse
from django import forms
from django.core.cache import cache
from django.apps import apps
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils.timezone import now
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS

from trapper.apps.common.tools import datetime_aware
from trapper.middleware import get_current_user
from trapper.apps.storage.models import Resource, Collection
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.media_classification.taxonomy import (
    ClassificatorSettings, ClassificationProjectRoleLevels,
    ClassificationProjectStatus, ClassificationStatus
)
from trapper.apps.media_classification.cachekeys import (
    get_form_fields_cache_name
)
from trapper.apps.common.fields import SafeTextField


def get_ordered_values(keys_list, d):
    """Return sorted values from dictionary by given list of keys"""
    return [d.get(k) for k in keys_list]


class ClassificationProjectManager(models.Manager):
    """Manager for :class:`ClassificationProject` model.

    This manager contains additional logic used byy DRF serializers like
    details/update/delete urls
    """
    url_update = 'media_classification:project_update'
    url_detail = 'media_classification:project_detail'
    url_delete = 'media_classification:project_delete'

    def api_update_context(self, item, user):
        """
        Method used in DRF api to return update url if user has permissions
        """
        context = None
        if item.can_update(user):
            context = reverse(self.url_update, kwargs={'pk': item.pk})
        return context

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        if item.can_view(user):
            context = reverse(self.url_detail, kwargs={'pk': item.pk})
        return context

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context

    def get_accessible(self, user=None, base_queryset=None, crowdsourcing=True):
        """Return all :class:`ClassificationProject` instances that given user
        has access to. If user is not defined, then currently logged in user
        is used.
        If there is no authenticated user then only classification projects
        with `crowdsourcing` enabled are returned

        :param user: if not none then that user will be used to filter
            accessible classification projects. If passed user not logged in,
            then projects are limited to those with `crowdsourcing` enabled.
            If user is None then currently logged in user is used.
        :param base_queryset: queryset used to limit checked projects.
            by default it's all projects.

        :return: classification project queryset
        """
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if user.is_authenticated():
            params = {
                'owner': user,
                'classification_project_roles__user': user,
            }
            if crowdsourcing:
                params.update({
                    'enable_crowdsourcing': True,
                })

            filter_params = reduce(
                operator.or_, map(models.Q, params.items())
            )
            queryset = queryset.filter(filter_params)
        else:
            queryset = queryset.filter(enable_crowdsourcing=True)

        return queryset.filter(disabled_at__isnull=True).distinct()


class ClassificationProject(models.Model):
    """
    Classification projects are containers for resource classifications.
    They are build on top of research project and can contain relation
    to research project collections from various research projects.

    Access to various operations on projects are described by
    :class:`ClassificationProjectRole` objects.

    Classification projects are last step linking resources and
    classifications.
    """

    name = models.CharField(max_length=255)
    research_project = models.ForeignKey(
        ResearchProject, related_name='classification_projects'
    )
    collections = models.ManyToManyField(
        ResearchProjectCollection, through='ClassificationProjectCollection',
        blank=True, related_name="classification_projects"
    )
    classificator = models.ForeignKey(
        'Classificator', related_name='classification_projects',
        blank=True, null=True
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL)
    date_created = models.DateTimeField(
        auto_now_add=True
    )
    status = models.IntegerField(
        choices=ClassificationProjectStatus.CHOICES,
        default=ClassificationProjectStatus.ONGOING
    )
    deployment_based_nav = models.BooleanField(
        "Deployment-based navigation", default=True, help_text="Enable deployment-based navigation"
    )
    enable_sequencing = models.BooleanField(
        "Sequences", default=True, help_text="Enable sequencing interface"
    )
    enable_crowdsourcing = models.BooleanField(
        default=True,
        help_text=u"Status if crowd-sourcing enabled for the project"
    )

    disabled_at = models.DateTimeField(blank=True, null=True, editable=False)
    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', 
        blank=True, null=True, editable=False
    )

    objects = ClassificationProjectManager()

    class Meta:
        ordering = ['-date_created']

    def __unicode__(self):
        return unicode(self.name)

    def is_finished(self):
        """Check if classification project is marked as finished"""
        return self.status == ClassificationProjectStatus.FINISHED

    def is_active(self):
        """Check if classification project is marked as **not** finished"""
        return self.status == ClassificationProjectStatus.ONGOING

    def get_classification_status(self, as_label=False):
        """Determine if project contains any approved classifications.
        Such project cannot be simply removed (see :func:`delete` for more
        details)

        :param as_label: boolean, if set to True, then status is given
            as label (determined from :class:`ClassificationStatus` choices
            that this model uses

        :return: project status boolean if `as_label` is False else string
        """
        status = self.classifications.filter(
            status=ClassificationStatus.APPROVED
        ).exists()
        if as_label:
            status_labels = ClassificationStatus.choices_as_dict()
            status = status_labels[status]
        return status

    def get_classification_stats(self):
        """
        Get list of resources that are assigned to this project.
        Then prepare stats as numbers:

        * approved - resources with approved classification
        * classified - resources with classifications (including approved
          classifications)
        * unclassified - resources without classification
        """

        user = get_current_user()
        res = Resource.objects.get_accessible(user=user, basic=True).filter(
            collection__researchprojectcollection__classificationprojectcollection__project=self
        ).count()

        classified = self.classifications.filter(
            user_classifications__isnull=False
        ).distinct()

        approved = classified.filter(
            status=True,
        ).count()
        classified = classified.count()
        unclassified = res - classified

        return {
            'approved': approved,
            'classified': classified,
            'unclassified': unclassified,
        }

    def get_roles(self):
        """
        Return mapping between users and their roles:

        .. code-block:: json

            {
                <user>: [<role_name>, <role_name>, ],
                <user>: [<role_name>, <role_name>, ],
            }
        """
        role_map = {}
        roles = self.classification_project_roles.all()
        for role in roles:
            role_map.setdefault(role.user, []).append(role)
        return role_map

    def get_user_roles_with_profiles(self):
        return self.classification_project_roles.all().select_related(
            'user', 'user__userprofile'
        )

    @property
    def classificator_removed(self):
        """Check if project has attached classificator.

        Not having classificator has strong influence on what can be done with
        project
        """
        return not self.classificator

    def is_project_admin(self, user=None):
        """Determine if given user has enough permissions to be marked as
        Project Admin (PA)

        If no user is given, then currently logged in is used.
        Anonymous users cannot be admins

        Value is stored on instance cache to prevent recalculating it in the
        same request multiple times
        """
        is_project_admin = getattr(self, '_is_project_admin', None)

        if is_project_admin is None:
            user = user or get_current_user()

            if user.is_authenticated():
                is_project_admin = (
                    self.owner == user or
                    self.classification_project_roles.filter(
                        user=user,
                        name=ClassificationProjectRoleLevels.ADMIN
                    ).exists()
                )
            else:
                is_project_admin = False
            self._is_project_admin = is_project_admin

        return is_project_admin

    def is_project_expert(self, user=None):
        """Determine if given user has enough permissions to be marked as
        project expert

        If no user is given, then currently logged in is used.
        Anonymous users cannot be experts
        """
        user = user or get_current_user()

        if user.is_authenticated():
            status = (
                self.owner == user or
                self.classification_project_roles.filter(
                    user=user,
                    name=ClassificationProjectRoleLevels.EXPERT
                ).exists()
            )
        else:
            status = False
        return status

    def get_user_roles(self, user=None):
        """Returns a tuple of project roles for given user.

        :return: list of role names of given user withing the project
        """
        user = user or get_current_user()
        roles = self.classification_project_roles.filter(user=user)
        return [r.get_name_display() for r in roles] 

    def can_view(self, user=None):
        """
        Checks if given user has access to details.

        :param user: if passed, permissions will be checked against given
            user will be used. If no user is given or user is not authenticated
            then access is denied.

        :return: boolean access status
        """
        user = user or get_current_user()
        if user.is_authenticated():
            return (
                self.owner == user or
                self.classification_project_roles.filter(user=user).exists()
            )

    def can_update(self, user=None):
        """
        Checks if given user can update project.

        :param user: if passed, permissions will be checked against given
            user will be used. If no user is given or user is not authenticated
            then access is denied.

        :return: boolean access status
        """
        user = user or get_current_user()
        if user.is_authenticated():
            return (
                self.owner == user or
                self.classification_project_roles.filter(
                    user=user, name__in=ClassificationProjectRoleLevels.UPDATE
                ).exists()
            )

    def can_delete(self, user=None):
        """
        Classification project can be deleted only:
        * by owner
        * by project admin user

        If project has approved classifictions, then it's not really
        deleted, but marked as disabled

        :param user: User instance
        :return: Boolean with access status
        """
        user = user or get_current_user()
        if user.is_authenticated():
            return (
                self.owner == user or
                self.classification_project_roles.filter(
                    user=user,
                    name__in=ClassificationProjectRoleLevels.DELETE
                ).exists()
            )

    def can_change_sequence(self, user=None):
        """
        Checks if given user can update sequence in project.

        :param user: if passed, permissions will be checked against given
            user will be used. If no user is given or user is not authenticated
            then access is denied.

        :return: boolean access status
        """
        user = user or get_current_user()
        return (
            (self.enable_sequencing and self.can_view(user=user)) or
            self.is_project_admin(user=user)
        )

    def is_sequencing_enabled(self, user=None):
        """Determine classify sequence box should be visible or not"""
        return self.enable_sequencing or self.is_project_admin(user=user)

    def can_view_classifications(self, user=None):
        """
        Checks if given user can view classifications made within project.

        :param user: if passed, permissions will be checked against given
            user will be used. If no user is given or user is not authenticated
            then access is denied.

        :return: boolean access status
        """
        user = user or get_current_user()
        return self.owner == user or self.classification_project_roles.filter(
            user=user,
            name__in=ClassificationProjectRoleLevels.VIEW_CLASSIFICATIONS
        ).exists()

    def get_absolute_url(self):
        """Get the absolute url for an instance of this model."""
        return reverse(
            'media_classification:project_detail',
            kwargs={'pk': self.pk}
        )

    def delete(self, *args, **kwargs):
        """
        If project has at least one classification that has been approved,
        then removing it could resolve in significant data and work lost.

        That's why before classification project removal, test is made
        to determine if project can be safely removed.

        If project cannot be safely removed, then `disabled_at` is set to
        current datetime, and `disabled_by` is set to user that is
        trying to remove project.

        If project can be safely removed, then standard logic is called
        and object is removed from database
        """
        if self.get_classification_status():
            user = get_current_user()
            self.disabled_at = datetime_aware()
            self.disabled_by = user
            self.save()
        else:
            super(ClassificationProject, self).delete(*args, **kwargs)


class ClassificationProjectRole(models.Model):
    """
    Model describing the user's role withing given
    :class:`ClassificationProject`
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='classification_project_roles',
        help_text=u"User for which the role is defined"
    )
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    name = models.IntegerField(choices=ClassificationProjectRoleLevels.CHOICES)

    classification_project = models.ForeignKey(
        ClassificationProject, related_name="classification_project_roles",
        help_text=u"Project for which the role is defined"
    )

    def __unicode__(self):
        return 'Classification project role: %s' % (self.pk)

    class Meta:
        ordering = ['user', 'name']
        unique_together = ('classification_project', 'user')


class ClassificationProjectCollectionManager(models.Manager):
    """Manager for :class:`ClassificationProjectCollection` model.

    This manager contains additional logic used byy DRF serializers like
    details/update/delete/classify urls
    """
    url_update = 'storage:collection_update'
    url_detail = 'storage:collection_detail'
    url_delete = 'media_classification:project_collection_delete'
    url_classify = 'media_classification:classify_collection'

    def get_accessible(self, user=None, base_queryset=None, role_levels=None):
        """Return all :class:`ClassificationProjectCollection` instances that
        given user has access to. If user is not defined, then currently
        logged in user is used.

        :param user: if not none then that user will be used to filter
            accessible classification projects.
        :param base_queryset: queryset used to limit checked collections,
            by default it's all collections.

        :return: classification project queryset
        """
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if user.is_authenticated():
            levels = role_levels or ClassificationProjectRoleLevels.ANY
            queryset = queryset.filter(
                models.Q(project__owner=user) |
                (
                    models.Q(
                        project__classification_project_roles__user=user
                    ) &
                    models.Q(
                        project__classification_project_roles__name__in=levels
                    )
                )
            )
        else:
            queryset = queryset.none()
        return queryset.filter(project__disabled_at__isnull=True).distinct()

    def api_update_context(self, item, user):
        """
        Method used in DRF api to return update url if user has permissions
        """
        context = None
        if item.can_update(user):
            context = reverse(
                self.url_update,
                kwargs={'pk': item.collection.pk}
            )
        return context

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        if item.can_view(user):
            context = reverse(
                self.url_detail,
                kwargs={'pk': item.collection.pk}
            )
        return context

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context

    def api_classify_context(self, item, user):
        """
        Method used in DRF api to return classify url if user has permissions
        """
        context = None
        if item.can_classify(user):
            context = reverse(
                self.url_classify,
                kwargs={
                    'project_pk': item.project.pk,
                    'collection_pk': item.pk
                }
            )
        return context


class ClassificationProjectCollection(models.Model):
    """model describes relation between :class:`ClassificationProject`
    and :class:`ClassificationProjectCollection` relationship."""

    project = models.ForeignKey(
        ClassificationProject,
        related_name='classification_project_collections'
    )
    collection = models.ForeignKey(
        ResearchProjectCollection, on_delete=models.PROTECT
    )
    is_active = models.BooleanField("Active", default=True)

    enable_sequencing_experts = models.BooleanField(
        "Sequences editable by experts", default=True,
        help_text="Allow experts to create and edit sequences"
    )

    enable_crowdsourcing = models.BooleanField(
        default=True,
        help_text=u"Status if crowd-sourcing enabled for the project"
    )

    objects = ClassificationProjectCollectionManager()

    def __unicode__(self):
        return unicode("%s" % self.collection)

    def get_resources(self, user=None, basic=False):
        """Returns all resources connected to this collection"""
        user = user or get_current_user()
        return self.collection.collection.resources.get_accessible(
            user=user, basic=basic
        )

    def get_unique_locations(self):
        """Returns all unique locations connected to this collection"""
        return set(self.collection.collection.resources.values_list(
            'deployment__location__pk', 'deployment__location__location_id'
        ))

    def can_delete(self, user=None):
        """
        ClassificationProjectCollection can be deleted when user has
        permissions to change ClassificationProject
        """
        user = user or get_current_user()
        return self.project.can_update(user=user)

    def can_view(self, user=None):
        """
        ClassificationProjectCollection can be accessed when user has
        permissions to view :class:`apps.storage.models.Collection`
        """
        user = user or get_current_user()
        return self.collection.collection.can_view(user=user)

    def can_update(self, user=None):
        """
        ClassificationProjectCollection can be updated when user has
        permissions to change :class:`apps.storage.models.Collection`
        """
        user = user or get_current_user()
        return self.collection.collection.can_update(user=user)

    def can_classify(self, user=None):
        """
        ClassificationProjectCollection can be used in classification when
        user has permissions to view ClassificationProject and
        project has assignec :class:`Classificator`
        """
        user = user or get_current_user()
        return (
            self.project.can_view(user=user) and
            self.project.classificator
        )

    def get_resources_classification_status(self, resources):
        """Return list of resources list with information about
        their classification status"""
        status_list = dict(Classification.objects.filter(
            project__pk=self.project.pk,
            resource__in=resources
        ).values_list('resource__pk', 'status'))

        return [(
            resource,
            status_list.get(resource.pk, ClassificationStatus.REJECTED)
        ) for resource in resources]

    def is_sequencing_enabled(self, user=None):
        """Determine if user can use sequencing interface buttons for given
        collection.
        This is especially useful when project has sequencing enabled
        but user has only expert role in project, so by using
        collection params, this interface can be disabled for experts.

        Value is stored on instance cache to prevent recalculating it in the
        same request multiple times
        """

        sequencing_enabled = getattr(self, '_sequencing_enabled', None)
        if sequencing_enabled is None:
            user = user or get_current_user()

            project = self.project
            admin = project.is_project_admin(user=user)

            sequencing_enabled = (
                admin or
                (
                    project.enable_sequencing and
                    project.is_project_expert(user=user) and
                    self.enable_sequencing_experts
                )
            )
            self._sequencing_enabled = sequencing_enabled
        return sequencing_enabled

    def rebuild_classifications(self):
        """
        This function is used by various signals to assure that classifications
        objects related to this classification project collection map to its
        resources.
        """
        collection_resources = self.collection.collection.resources.values_list('pk', flat=True)
        classification_resources = self.classifications.values_list('resource__pk', flat=True)
        diff_pks = set(collection_resources).difference(classification_resources)
        # bulk create of missing classifications objects
        insert_list = []
        for pk in diff_pks:
            obj = Classification(
                resource_id=pk,
                collection=self,
                project_id=self.project_id,
                created_at=now(),
                status=ClassificationStatus.REJECTED,
                updated_at=now()
            )
            insert_list.append(obj)
        Classification.objects.bulk_create(insert_list)


class ClassificatorManager(hstore.HStoreManager):
    """Manager for :class:`Classificator` model.

    This manager contains additional logic used byy DRF serializers like
    details/update/delete urls
    """
    url_update = 'media_classification:classificator_update'
    url_detail = 'media_classification:classificator_detail'
    url_delete = 'media_classification:classificator_delete'

    def api_update_context(self, item, user):
        """
        Method used in DRF api to return update url if user has permissions
        """
        context = None
        if item.can_update(user):
            context = reverse(self.url_update, kwargs={'pk': item.pk})
        return context

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        if item.can_view(user):
            context = reverse(self.url_detail, kwargs={'pk': item.pk})
        return context

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context

    def get_accessible(self, user=None):
        """Authenticated users can see all non-deleted classificators"""
        user = user or get_current_user()
        if user.is_authenticated():
            queryset = self.get_queryset()
        else:
            queryset = self.none()
        return queryset.filter(disabled_at__isnull=True)


class Classificator(models.Model):
    """Defined group of attributes describing given classification form.
    Such set is defined per-resource type, and is defined in given
    classification project.
    """
    SEPARATOR = ','
    CLONE_PATTERN = u"Copy_of_{count}_{name}"

    name = models.CharField(max_length=255, unique=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='user_classificators'
    )

    custom_attrs = hstore.DictionaryField(null=True, blank=True)
    predefined_attrs = hstore.DictionaryField(null=True, blank=True)
    dynamic_attrs_order = models.TextField(null=True, blank=True)
    static_attrs_order = models.TextField(null=True, blank=True)
    updated_date = models.DateTimeField(blank=True, auto_now=True)
    created_date = models.DateTimeField(blank=True, auto_now_add=True)
    description = SafeTextField(max_length=2000, null=True, blank=True)

    copy_of = models.ForeignKey(
        'self', blank=True, null=True, related_name='+', editable=False
    )
    disabled_at = models.DateTimeField(blank=True, null=True, editable=False)
    disabled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', blank=True, null=True, editable=False
    )
    template = models.CharField(
        max_length=50,
        choices=ClassificatorSettings.TEMPLATE_CHOICES,
        default=ClassificatorSettings.TEMPLATE_INLINE
    )

    objects = ClassificatorManager()

    def __unicode__(self):
        return self.name

    def save(self, **kwargs):
        """Set `created_date` for newly created classificator, and
        `updated_date` when classificator is changed"""
        super(Classificator, self).save(**kwargs)

        # Clear form fields cache
        cache_name = get_form_fields_cache_name(self)
        cache.delete(cache_name)

    def delete(self, *args, **kwargs):
        """
        If project has at least one classification that has been approved,
        then removing classificator could resolve in significent data and work
        lost.

        That's why before classifcatorremoval, test is made
        to determine if it can be safetly removed.

        If classificator cannot be safetly removed, then `disabled_at` is set
        to current datetime, and `disabled_by` is set to user that is
        trying to remove classificator.

        If clssificator can be safetly removed, then standard logic is called
        and object is removed from database
        """
        status = self.get_classification_status()
        if status:
            user = get_current_user()
            self.disabled_at = datetime_aware()
            self.disabled_by = user
            self.save()
        else:
            super(Classificator, self).delete(*args, **kwargs)

    def get_classification_status(self):
        for project in self.classification_projects.all():
            if project.get_classification_status():
                return True
        return False

    def get_absolute_url(self):
        """Return url of research project details"""
        return reverse(
            'media_classification:classificator_detail', kwargs={'pk': self.pk}
        )

    def can_view(self, user=None):
        """Determines whether given user can see the details of a classificator.

        This method always return True, because everyone can view
        classificators, but defining this as method fits commonly used api
        for testing access.

        :param: user :class:`auth.User` instance for which test is made
        :return: True
        """
        return True

    def can_update(self, user=None):
        """Determines whether given user can update the classificator.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can update classificator, False otherwise
        """
        user = user or get_current_user()
        return self.owner == user

    def can_delete(self, user=None):
        """Determines whether given user can delete the classificator.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can delete classificator, False otherwise
        """
        user = user or get_current_user()
        return self.owner == user

    @property
    def active_predefined_attr_names(self):
        """
        Return list of predefined attribute names that are used in
        classificator
        :return: list of names
        """
        config = (
            ClassificatorSettings.PREDEFINED_ATTRIBUTES_SIMPLE.keys() +
            ClassificatorSettings.PREDEFINED_ATTRIBUTES_MODELS.keys()
        )
        active = []
        for attr in config:
            static_attr = self.predefined_attrs.get(attr, None)

            if static_attr == 'true':
                active.append(attr)
        return active

    def get_all_attrs_names(self):
        """
        Return list of all attribute names that are used in classificator
        :return: list of names
        """
        all_items = [[], []]  # [[dynamic_form], [static_form]]
        for at in self.active_predefined_attr_names:
            if self.predefined_attrs['target_%s' % at] == 'D':
                all_items[0].append(at)
            else:
                all_items[1].append(at)
        for at in self.custom_attrs.keys():
            if json.loads(self.custom_attrs[at])['target'] == 'D':
                all_items[0].append(at)
            else:
                all_items[1].append(at)
        return all_items

    def _get_attrs_order(self, data):
        """
        Convert given attribute order into list
        @:param data: string that will be splitted
        @:return: list of splitted items or empty list
        """
        items = []
        if data:
            try:
                items = data.split(self.SEPARATOR)
            except (ValueError, AttributeError):
                pass
        return items

    def get_dynamic_attrs_order(self):
        """Dynamic attribute order is stored as comma separated list of
        names. They need to be converted to standard list to be
        """
        return self._get_attrs_order(data=self.dynamic_attrs_order)

    def get_static_attrs_order(self):
        """Static attribute order is stored as comma separated list of
        names. They need to be converted to standard list to be
        """
        return self._get_attrs_order(data=self.static_attrs_order)

    def update_attrs_order(self):
        """Recalculate attribute order when classificator has been changed"""
        all_attrs_names = self.get_all_attrs_names()
        dynamic_attrs_order = self.get_dynamic_attrs_order()
        static_attrs_order = self.get_static_attrs_order()
        for at in all_attrs_names[0]:  # dynamic_form
            if at not in dynamic_attrs_order:
                dynamic_attrs_order.append(at)
        for at in dynamic_attrs_order:
            if at not in all_attrs_names[0]:
                del dynamic_attrs_order[dynamic_attrs_order.index(at)]

        for at in all_attrs_names[1]:  # static_form
            if at not in static_attrs_order:
                static_attrs_order.append(at)
        for at in static_attrs_order:
            if at not in all_attrs_names[1]:
                del static_attrs_order[static_attrs_order.index(at)]
        self.dynamic_attrs_order = ','.join(dynamic_attrs_order)
        self.static_attrs_order = ','.join(static_attrs_order)
        self.save()

    def parse_hstore_values(self, field, attr=None):
        """Hstore values are stored in database as strings.
        Before thay can be used they need to be converted into dictionary

        :param field: name of field that has to be parsed.
        :param attr: optional attribute name to parse

        :return: if specified, then only single value from `field` will be
            returned, otherwise all values defined on `field` are returned
        """
        parsed_values = {}
        # if attr not specified parse all
        if not attr:
            items = getattr(self, field).items()
        else:
            values = getattr(self, field)
            if values:
                items = [(attr, values[attr], ), ]
            else:
                items = []
        for k, v in items:
            try:
                parsed_values[k] = json.loads(v)
            except ValueError:
                # if it is not a json it must be a simple string so just
                # add it to a parsed_values dict
                parsed_values[k] = v
        return parsed_values

    def prepare_form_fields(self):
        """
        Since classificator is a collection of user-defined fields these
        fields are used to generate the classification form. This method is
        responsible for converting a definition of classificator into a structured
        list of form fields.
        """
        
        cache_name = get_form_fields_cache_name(self)
        form_fields = cache.get(cache_name, settings.CACHE_UNDEFINED)

        if form_fields is settings.CACHE_UNDEFINED:
            # parsed predefined attributes
            predefined_attrs = self.parse_hstore_values('predefined_attrs')
            form_fields = OrderedDict()
            form_fields['D'] = OrderedDict()  # "D" -> dynamic form
            form_fields['S'] = OrderedDict()  # "S" -> dynamic form
            # first prepare predefined attributes:
            pas = ClassificatorSettings.PREDEFINED_ATTRIBUTES_SIMPLE
            for key, val in pas.iteritems():
                if predefined_attrs.get(key):
                    params = {
                        'required': predefined_attrs['required_%s' % key]
                    }
                    widget = val.get('widget', None)
                    if widget:
                        params['widget'] = widget

                    formfield = val['formfield'](**params)

                    # This is required for special rendering annotation widget
                    form_fields[predefined_attrs[
                        'target_%s' % key
                    ]][key] = formfield

            pam = ClassificatorSettings.PREDEFINED_ATTRIBUTES_MODELS
            for key, val in pam.iteritems():
                if predefined_attrs.get(key):
                    model = apps.get_model(pam[key]['app'], key)
                    selected_key = 'selected_%s' % key

                    if predefined_attrs[selected_key]:
                        query = model.objects.filter(
                            pk__in=predefined_attrs[selected_key]
                        )
                    else:
                        query = model.objects.all()
                    values_key = pam[key]['choices_labels']
                    choices = query.values_list(values_key, values_key)
                    choices = [('','---------'),] + list(choices)

                    formfield = forms.ChoiceField(
                        choices=choices,
                        required=predefined_attrs['required_%s' % key]
                    )

                    target_key = predefined_attrs['target_%s' % key]
                    form_fields[target_key][key] = formfield

            # parsed custom attributes
            custom_attrs = self.parse_hstore_values('custom_attrs')
            # next prepare custom attributes:
            for key in custom_attrs:
                dynamic_item = custom_attrs[key]
                values_key = dynamic_item['values']
                if values_key:
                    # values have been already checked during a form validation
                    # so just split them
                    if not isinstance(values_key, list):
                        splitted_values = values_key.split(',')
                    else:
                        splitted_values = values_key
                    choices = zip(splitted_values, splitted_values)
                    formfield = forms.ChoiceField(
                        choices=choices, required=dynamic_item['required'],
                        initial=dynamic_item['initial']
                    )
                else:
                    fields_key = dynamic_item['field_type']
                    formfield = ClassificatorSettings.FIELDS[fields_key](
                        required=dynamic_item['required'],
                        initial=dynamic_item['initial'],
                    )
                form_fields[dynamic_item['target']][key] = formfield

            # re-order field forms
            dao = self.get_dynamic_attrs_order()
            form_fields['D'] = OrderedDict((k, form_fields['D'][k]) for k in dao)
            sao = self.get_static_attrs_order()
            form_fields['S'] = OrderedDict((k, form_fields['S'][k]) for k in sao)

            cache.set(cache_name, form_fields, settings.CACHE_TIMEOUT)
        return form_fields

    def remove_custom_attr(self, name, commit=False):
        """Remove given name from custom attributes

        :param name: name of attribute to be removed
        :commit: boolean, if set to True then after removal
            classificator will be removed
        """
        if name in self.dynamic_attrs_order:
            order = self.get_dynamic_attrs_order()
            order.remove(name)
            self.dynamic_attrs_order = ",".join(order)
        if name in self.static_attrs_order:
            order = self.get_static_attrs_order()
            order.remove(name)
            self.static_attrs_order = ",".join(order)
        del self.custom_attrs[name]

        if commit:
            self.save()

    def set_custom_attr(self, name, params, commit=False):
        """Set custom attribute with given values.

        :param name: name of attribute to be set
        :param params: dictionary with parameters that should be set under
            attribute name

        :commit: boolean, if set to True then after removal
            classificator will be removed
        """
        static_order = self.get_static_attrs_order()
        dynamic_order = self.get_dynamic_attrs_order()

        try:
            initial = self.parse_hstore_values('custom_attrs', name)[name]
        except KeyError:
            initial = params
        else:
            initial.update(params)

        if initial['field_type'] == 'B':
            initial['values'] = [False, True]

        target = params['target']
        if target == 'S':
            if name not in static_order:
                static_order.append(name)
            if name in dynamic_order:
                dynamic_order.remove(name)
        elif target == 'D':
            if name not in dynamic_order:
                dynamic_order.append(name)
            if name in static_order:
                static_order.remove(name)

        self.static_attrs_order = u",".join(static_order)
        self.dynamic_attrs_order = u",".join(dynamic_order)
        if self.custom_attrs:
            self.custom_attrs[name] = initial
        else:
            self.custom_attrs = {name: initial}
        if commit:
            self.save()

    def set_predefined_attrs(self, predefined_data, commit=False):
        """Set predefined aattributes with given data.

        :param predefined_data: dictionary with parameters that
            should be set

        :commit: boolean, if set to True then after removal
            classificator will be removed
        """

        for attribute in predefined_data:
            if attribute.startswith('selected_'):
                name = attribute.replace('selected_', '', 1)
                if predefined_data[name]:
                    values = [
                        item.pk for item in predefined_data[attribute]
                    ]
                else:
                    values = []
                predefined_data[attribute] = values

            if attribute.startswith('required_'):
                name = attribute.replace('required_', '', 1)
                predefined_data[attribute] = (
                    predefined_data[name] and
                    predefined_data[attribute]
                )
            if attribute.startswith('target_'):
                name = attribute.replace('target_', '', 1)
                static_order = self.get_static_attrs_order()
                dynamic_order = self.get_dynamic_attrs_order()
                target = predefined_data[attribute]
                is_checked = predefined_data[name]
                if is_checked:
                    if target == 'S':
                        if name not in static_order:
                            static_order.append(name)
                        if name in dynamic_order:
                            dynamic_order.remove(name)
                    elif target == 'D':
                        if name not in dynamic_order:
                            dynamic_order.append(name)
                        if name in static_order:
                            static_order.remove(name)
                else:
                    if name in static_order:
                        static_order.remove(name)
                    elif name in dynamic_order:
                        dynamic_order.remove(name)
                self.static_attrs_order = u",".join(static_order)
                self.dynamic_attrs_order = u",".join(dynamic_order)
        self.predefined_attrs = predefined_data

        if commit:
            self.save()


class ClassificationManager(hstore.HStoreManager):
    """Manager for :class:`Classification` model.

    This manager contains additional logic used by DRF serializers
    """
    url_detail = 'media_classification:classify'
    url_delete = 'media_classification:classification_delete'

    def get_accessible(self, user=None, base_queryset=None, role_levels=None):
        """Return all :class:`Classification` instances that given user
        has access to. If user is not defined, then currently logged in user
        is used.
        If there is no authenticated user, then empty queryset is returned

        :param user: if not none then that user will be used to filter
            accessible classifications. If passed user not logged in,
            then empty queryset is returned
            If user is None then currently logged in user is used.
        :param base_queryset: queryset used to limit checked classifications.
            by default it's all classifications.
        :param role_levels:

        :return: classifications queryset
        """
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            queryset = queryset.none()
        else:
            levels = role_levels or ClassificationProjectRoleLevels.VIEW_CLASSIFICATIONS
            cprojects = user.classification_project_roles.filter(name__in=levels).values_list(
                'classification_project_id', flat=True
            )
            queryset = queryset.filter(
                models.Q(project__owner=user) | models.Q(project__in=cprojects) 
            )
        return queryset

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        if item.can_view(user):
            context = reverse(
                self.url_detail,
                kwargs={
                    'pk': item.pk
                }
            )
        return context

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class Classification(models.Model):
    """
    This is destination place for all work that is done with resources.
    Classification is always related to :class:`ClassificationProject` and
    single :class:`apps.storage.models.Resouce`.

    Resource classification is process where user, using form provided by
    :class:`Classificator` assigned to project, describe and evaluate given
    resource. This evaluation can be used leter in classification lists where
    it can be i.e. compared to other classifications of the same resource by
    other users in other classification projects.
    """

    resource = models.ForeignKey(Resource, related_name='classifications')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='classifications_created'
    )
    created_at = models.DateTimeField(auto_created=True)
    project = models.ForeignKey(
        ClassificationProject, related_name='classifications'
    )
    collection = models.ForeignKey(
        ClassificationProjectCollection, related_name='classifications'
    )
    sequence = models.ForeignKey(
        'Sequence', null=True, blank=True, related_name='classifications',
        on_delete=models.SET_NULL
    )
    static_attrs = hstore.DictionaryField(null=True, blank=True)
    status = models.BooleanField(
        default=False, choices=ClassificationStatus.CHOICES
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='classifications_approved'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_source = models.OneToOneField(
        'UserClassification', null=True, blank=True,
        related_name='classification_approved',
        on_delete=models.SET_NULL
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name='classifications_updated'
    )
    updated_at = models.DateTimeField(null=True, blank=True)

    objects = ClassificationManager()

    class Meta:
        ordering = ('resource__date_recorded', )

    def __unicode__(self):
        return unicode(
            u"Classification: %s" % (self.pk)
        )

    @property
    def classificator(self):
        """Return classificator assigned to classification"""
        return self.project.classificator

    @property
    def is_approved(self):
        """Return True if classification is approved, False otherwise"""
        return self.status == ClassificationStatus.APPROVED

    @property
    def is_rejected(self):
        """Return True if classification is rejected, False otherwise"""
        return self.status == ClassificationStatus.REJECTED

    def get_user_classifications(self):
        """Return all user classifications that are connected to this
        classification.
        This method can be used to determine how often given resource
        was classified by users"""
        return self.user_classifications.all().order_by('updated_date')

    def can_view(self, user=None):
        """Check if given user (or currently logged in) can view details
        of classification.

        By default persons that have access to project can view classifications
        done within that project.
        """
        return self.project.can_view(user=user)

    def can_update(self, user=None):
        """Check if given user (or currently logged in) can update given
        classification

        By default Owner and project admin can update classification.
        """
        user = user or get_current_user()
        return (
            self.owner == user or self.project.is_project_admin(user=user)
        )

    def can_approve(self, user=None):
        """Check if given user (or currently logged in) can approve
        classification using classification box in classification details
        (this could be done from different classification details)

        By default only project admin can approve classification
        """
        return self.project.is_project_admin(user=user)

    def can_delete(self, user=None):
        """Check if given user (or currently logged in) can delete
        classification

        By default only project admin can approve classification
        """
        user = user or get_current_user()
        return self.project.is_project_admin(user=user)

    def delete(self, clear=False, *args, **kwargs):
        """If `clear` is True just clear all classification's data;
        do not delete the object itself."""
        if clear:
            user = get_current_user()
            self.static_attrs = {}
            self.dynamic_attrs.all().delete()
            self.status = False
            self.approved_by = None
            self.approved_at = None
            self.approved_source = None
            self.updated_at = now()
            self.updated_by = user
            self.save()
        else:
            super(Classification, self).save(*args, **kwargs)


class ClassificationDynamicAttrs(models.Model):
    """Each :class:`Classification` can contain multiple dynamic attributes and
    their values.
    Those values are stored in this model.
    """
    classification = models.ForeignKey(
        Classification, related_name='dynamic_attrs'
    )
    attrs = hstore.DictionaryField(null=True, blank=True)

    objects = hstore.HStoreManager()

    def __unicode__(self):
        return unicode(self.attrs)[:50]


class UserClassificationManager(hstore.HStoreManager):
    """Manager for :class:`UserClassification` model.

    This manager contains additional logic used by DRF serializers
    """
    url_detail = 'media_classification:classification_detail'
    #url_delete = 'media_classification:user_classification_delete'

    def get_accessible(self, user=None, base_queryset=None):
        """
        """
        user = user or get_current_user()

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            queryset = queryset.none()
        else:
            levels = ClassificationProjectRoleLevels.VIEW_USER_CLASSIFICATIONS
            cprojects = user.classification_project_roles.filter(name__in=levels).values_list(
                'classification_project_id', flat=True
            )
            queryset = queryset.filter(
                models.Q(classification__project__owner=user) |
                models.Q(classification__project__in=cprojects)
            )            
        return queryset

    def api_detail_context(self, item, user):
        """
        Method used in DRF api to return detail url if user has permissions
        """
        context = None
        if item.can_view(user):
            context = reverse(
                self.url_detail,
                kwargs={
                    'pk': item.pk
                }
            )
        return context

    # def api_delete_context(self, item, user):
    #     """
    #     Method used in DRF api to return delete url if user has permissions
    #     """
    #     context = None
    #     if item.can_delete(user):
    #         context = reverse(self.url_delete, kwargs={'pk': item.pk})
    #     return context


class UserClassification(models.Model):
    """
    Before final classification is approved and saved each user can
    create own classification that is stored in this model.

    When Project Admin approves selected user classification then values from
    this classificationare transferred into :class:`Classification` object.
    """

    classification = models.ForeignKey(
        Classification, related_name="user_classifications",
    )
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='user_classifications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    static_attrs = hstore.DictionaryField(null=True, blank=True)

    objects = UserClassificationManager()

    def __unicode__(self):
        return unicode(
            u"User classification: %s" % (self.pk)
        )

    @property
    def classificator(self):
        """Return classificator assigned to classification"""
        return self.classification.classificator

    def get_static_values(self):
        """Return ordered static values assigned to classificator"""
        predefined_order = \
            self.classification.classificator.get_static_attrs_order()
        return get_ordered_values(predefined_order, self.static_attrs)

    def get_custom_values(self):
        """Return ordered static values assigned to classificator"""
        values_list = []
        custom_order = \
            self.classification.classificator.get_dynamic_attrs_order()
        for row in self.custom_attrs.values_list('attrs', flat=True):
            values_list.append(
                get_ordered_values(custom_order, row)
            )
        return values_list

    def can_view(self, user=None):
        """Check if given user (or currently logged in) can view details
        of classification.

        By default persons that have access to project can view classifications
        done within that project.
        """
        return self.classification.project.can_view(user=user)

    def can_update(self, user=None):
        """Check if given user (or currently logged in) can update given
        classification

        By default Owner and project admin can update classification.
        """
        user = user or get_current_user()
        return (
            self.owner == user or
            self.classification.project.is_project_admin(user=user)
        )

    def can_delete(self, user=None):
        return self.can_update(user=user)


class UserClassificationDynamicAttrs(models.Model):
    """Each :class:`UserClassification` can contain multiple dynamic attributes
    and their values.
    Those values are stored in this model.

    When classification is approved, dynamic attributes from this model
    are transferred into :class:`ClassificationDynamicAttrs`
    """
    userclassification = models.ForeignKey(
        UserClassification, related_name='dynamic_attrs'
    )
    attrs = hstore.DictionaryField()

    objects = hstore.HStoreManager()

    def __unicode__(self):
        return unicode(self.attrs)[:50]


class Sequence(models.Model):
    """
    Sequence of resources identified by an expert (ADMIN or EXPERT
    in a project).
    """

    sequence_id = models.IntegerField(null=True, blank=True)
    description = models.TextField(max_length=1000, null=True, blank=True)
    collection = models.ForeignKey(
        ClassificationProjectCollection, related_name='sequences'
    )
    resources = models.ManyToManyField(Resource, through='SequenceResourceM2M')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL)

    class Meta:
        ordering = ['sequence_id',]

    def __unicode__(self):
        return 'Sequence: %s' % (self.pk)

    def save(self, *args, **kwargs):
        if self.id is None:
            last_obj = self.__class__.objects.filter(
                collection=self.collection
            ).order_by('sequence_id').last()
            if last_obj:
                self.sequence_id = last_obj.sequence_id + 1
            else:
                self.sequence_id = 1
        super(self.__class__, self).save(*args, **kwargs)

    def get_absolute_url(self):
        """Return url of research project details"""
        return reverse(
            'media_classification:sequence_detail', kwargs={'pk': self.pk}
        )

    def can_delete(self, user=None):
        """Determines whether given user can delete sequence.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can delete sequence, False otherwise
        """
        user = user or get_current_user()
        project = self.collection.project
        return (
            (self.created_by == user and project.enable_sequencing) or
            project.is_project_admin(user=user)
        )


class SequenceResourceM2M(models.Model):

    sequence = models.ForeignKey(Sequence)
    resource = models.ForeignKey(Resource)

    def validate_unique(self, *args, **kwargs):
        super(SequenceResourceM2M, self).validate_unique(*args, **kwargs)
        if not self.id:
            if self.__class__.objects.exclude(sequence=self.sequence).filter(
                    sequence__collection=self.sequence.collection,
                    resource=self.resource
            ).exists():
                raise ValidationError(
                    {
                        NON_FIELD_ERRORS: [
                            'The resource <bold>{resource}</bold> is already a part '
                            'of another sequance'.format(resource=self.resource.name)
                        ],
                    }
                )


class ClassificatorHistory(models.Model):
    """This model is used to provide history of classificator changes
    within classification projects.
    This can be used (i.e. by admins) fix issues when classificator is
    by mistake removed from classification project that has no approved
    classifications"""
    classification_project = models.ForeignKey(
        ClassificationProject, related_name='classificator_history'
    )
    classificator = models.ForeignKey(
        Classificator, related_name='classificator_history',
        blank=True, null=True
    )
    change_date = models.DateTimeField(auto_now_add=True, editable=False)


@receiver(pre_save, sender=ClassificationProject)
def classificator_history(sender, **kwargs):
    """
    Signal used to register changes of classificator within classification
    project
    """
    instance = kwargs.get('instance')
    if instance.pk:
        old_instance = sender.objects.get(pk=instance.pk)
        if old_instance.classificator != instance.classificator:
            ClassificatorHistory.objects.create(
                classification_project=instance,
                classificator=old_instance.classificator
            )


@receiver(post_save, sender=ClassificationProjectRole)
def project_role_collections_access_grant(sender, instance, **kwargs):
    """
    """
    from trapper.apps.storage.models import collections_access_grant
    user = instance.user

    if not ClassificationProjectRole.objects.filter(
            classification_project__pk=instance.classification_project_id,
            user=user
    ).exclude(
            pk=instance.pk
    ).exclude(
        user__pk=instance.classification_project.owner_id
    ).exists():
        collections_pks = instance.classification_project.collections.values_list(
            'collection__pk', flat=True
        )
        collections = Collection.objects.filter(
            pk__in=collections_pks
        ).prefetch_related('managers')

        collections_access_grant(
            users=[user],
            collections=collections
        )


@receiver(post_delete, sender=ClassificationProjectRole)
def project_role_collections_access_revoke(sender, instance, **kwargs):
    """
    """
    from trapper.apps.storage.models import collections_access_revoke
    user = instance.user
    if not ClassificationProjectRole.objects.filter(
            classification_project__pk=instance.classification_project_id,
            user=user
    ).exclude(
            pk=instance.pk
    ).exclude(
            user__id=instance.classification_project.owner_id
    ).exists():
        collection_pks = instance.classification_project.collections.values_list(
            'collection__pk', flat=True
        )

        collections_access_revoke(
            collection_pks=collection_pks,
            user_pks=[user.pk],
            cproject=True
        )


@receiver(post_save, sender=ClassificationProjectCollection)
def project_collections_access_grant(sender, instance, **kwargs):
    """
    Signal used to grant an access to collections that belong to the
    classification project for users that are a part of this project.
    """
    if kwargs['created']:
        from trapper.apps.storage.models import collections_access_grant
        roles = ClassificationProjectRole.objects.filter(
            classification_project=instance.project
        ).exclude(
            user=instance.project.owner
        ).prefetch_related('user')
        users = set([item.user for item in roles])

        collections_access_grant(
            users=users,
            collections=[instance.collection.collection,]
        )


@receiver(post_delete, sender=ClassificationProjectCollection)
def project_collections_access_revoke(sender, instance, **kwargs):
    """
    Signal used to revoke an access to collections that belong to the
    classification project for users that are not a part of this project
    anymore.
    """
    from trapper.apps.storage.models import collections_access_revoke
    user_pks = ClassificationProjectRole.objects.filter(
        classification_project=instance.project
    ).exclude(
        user=instance.project.owner
    ).values_list('user__pk', flat=True)

    collections_access_revoke(
        user_pks=user_pks,
        collection_pks=[instance.collection.collection.pk,],
        cproject=True
    )


@receiver(post_save, sender=ClassificationProjectCollection)
def project_collection_rebuild_(sender, instance, **kwargs):
    instance.rebuild_classifications()

