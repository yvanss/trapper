# -*- coding: utf-8 -*-
"""Module contains models and signals for research application and
permissions related to them."""
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.core.mail import mail_admins, send_mail
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

from trapper.middleware import get_current_user
from trapper.apps.research.taxonomy import (
    ResearchProjectRoleType, ResearchProjectStatus
)
from trapper.apps.messaging.models import Message
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.common.fields import SafeTextField
from trapper.middleware import get_current_request
from trapper.apps.storage.taxonomy import (
    CollectionStatus, CollectionMemberLevels
)
from trapper.apps.common.tools import datetime_aware

from taggit.managers import TaggableManager


class ResearchProjectManager(models.Manager):
    """Manager for :class:`ResearchProject` model.

    This manager contains additional logic used by DRF serializers.
    """
    url_update = 'research:project_update'
    url_detail = 'research:project_detail'
    url_delete = 'research:project_delete'

    def get_accessible(self, user=None, base_queryset=None, role_levels=None):
        """
        Return all :class:`ResearchProject` instances that given user
        has access to.

        :param user: if not none then that user will be used to filter
            accessible research projects.
        :param base_queryset: queryset used to limit checked research projects.
            by default it's all projects.

        :return: research projects queryset
        """

        user = user or get_current_user()

        if not user.is_authenticated():
            return ResearchProject.objects.none()

        if base_queryset is None:
            queryset = super(ResearchProjectManager, self).get_queryset()
        else:
            queryset = base_queryset

        if user is not None and user.pk and role_levels:

            queryset = queryset.filter(
                Q(owner=user) |
                (
                    Q(project_roles__user=user) &
                    Q(project_roles__name__in=role_levels)
                )
            ).distinct()
        return queryset.filter(status=True)

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
        Method used in DRF api to return detail url

        Everyone can see details of research project.
        If user is not logged in or has no proper rights
        only short version is visible"""
        return reverse(self.url_detail, kwargs={'pk': item.pk})

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.can_delete(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class ResearchProject(models.Model):
    """
    Research projects are entities for grouping collections (and by that
    resources) for future processing.

    Access to various operations on projects are described by
    :class:`ResearchProjectRole` objects.

    Research project is a kind of a middle-step between resources and classifications.
    """

    name = models.CharField(max_length=255, unique=True)
    acronym = models.CharField(max_length=10, unique=True)
    description = SafeTextField(max_length=2000, null=True, blank=True)
    abstract = SafeTextField(max_length=2000, null=True, blank=True)
    methods = SafeTextField(max_length=2000, null=True, blank=True)

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='research_projects')
    collections = models.ManyToManyField(
        'storage.Collection', through='ResearchProjectCollection', blank=True,
        related_name='research_projects'
    )
    date_created = models.DateTimeField(auto_now_add=True)

    status = models.NullBooleanField(choices=ResearchProjectStatus.CHOICES)
    status_date = models.DateTimeField(blank=True, null=True, editable=False)

    keywords = TaggableManager()
    objects = ResearchProjectManager()

    class Meta:
        ordering = ['-status_date']

    def __unicode__(self):
        return unicode(self.acronym)

    def get_roles(self):
        """Return mapping between users and their roles:

        .. code-block:: python
            {
                <user>: [<role_name>, <role_name>, ...],
                <user>: [<role_name>, <role_name>, ...],
                ...
            }
        """
        role_map = {}
        roles = self.project_roles.all()
        for role in roles:
            role_map.setdefault(role.user, []).append(role)
        return role_map

    def get_user_roles(self, user=None):
        """Returns a tuple of project roles for given user.

        :param: user :class:`auth.User` instance for which the roles are
            determined
        :return: list of role names of given user withing the project
        """
        user = user or get_current_user()
        roles = self.project_roles.filter(user=user)
        return [role.get_name_display() for role in roles]

    def get_user_roles_with_profiles(self):
        return self.project_roles.all().select_related(
            'user', 'user__userprofile'
        )
    def can_update(self, user=None):
        """Determines whether given user can update the project.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can update project, False otherwise
        """
        user = user or get_current_user()

        return self.status is True and user.is_authenticated() and (
            self.owner == user or self.project_roles.filter(
                user=user, name__in=ResearchProjectRoleType.EDIT
            ).exists()
        )

    def can_delete(self, user=None):
        """Determines whether given user can delete the project.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can delete the project, False otherwise
        """
        user = user or get_current_user()

        return self.status is True and user.is_authenticated() and (
            self.owner == user or
            self.project_roles.filter(
                user=user, name__in=ResearchProjectRoleType.DELETE
            ).exists()
        )

    def can_view(self, user=None):
        """Determines whether given user can see the details of a project.

        :param: user :class:`auth.User` instance for which test is made
        :return: True if user can see the details of the project,
            False otherwise
        """
        user = user or get_current_user()

        return self.status is True and user.is_authenticated() and (
            self.owner == user or self.project_roles.filter(
                user=user
            ).exists()
        )

    def can_create_classification_project(self, user=None):
        """Determine if user can use this project to create classification
        project"""
        return self.can_view(user=user)

    def get_absolute_url(self):
        """Return url of research project details"""
        return reverse('research:project_detail', kwargs={'pk': self.pk})

    def save(self, **kwargs):
        """
        If project has been accepted, then accept date is set,
        also when project is created, two notifications are sent:

        * to user, that project has been created
        * to admins, that project has been created and waiting for
          approve or decline
        """

        if (
            self.status is not None and
            self.status_date is None
        ):
            self.status_date = datetime_aware()
        super(ResearchProject, self).save(**kwargs)

    def get_admin_url(self):
        """
        Get full url to the research project change view in 
        admin based on project.pk
        """
        request = get_current_request()
        return request.build_absolute_uri(
            reverse(
                'admin:research_researchproject_change', 
                args=(self.pk,)
            )
        )

    def send_create_message(self):
        """Notify all django admins about new project using
        :class:`apps.messaging.models.Message` (application messaging)
        """
        User = get_user_model()
        recipients = User.objects.filter(
            is_active=True, is_superuser=True
        )

        body_template = (
            'New research project has been created. You can approve or reject it '
            'by changing its status at:\n'
            '{url}'
        ).format(
            url=reverse(
                'admin:research_researchproject_change', args=(self.pk,)
            )
        )

        for recipient in recipients:
            Message.objects.create(
                subject=(
                    u"New research project: <strong>{name}</strong> "
                    u"created"
                ).format(
                    name=self.name
                ),
                text=body_template,
                user_from=self.owner,
                user_to=recipient,
                date_sent=datetime_aware(),
                message_type=MessageType.RESEARCH_PROJECT_CREATED
            )


class ResearchProjectRole(models.Model):
    """
    Model describing the user's role withing given :class:`ResearchProject`
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='research_project_roles')
    project = models.ForeignKey(ResearchProject, related_name='project_roles')
    date_created = models.DateTimeField(auto_now_add=True, editable=False)
    name = models.SmallIntegerField(
        choices=ResearchProjectRoleType.CHOICES
    )

    def __unicode__(self):
        return unicode(
            "%s | Project: %s | Role: %s " % (
                self.user.username, self.project.name, self.get_name_display()
            )
        )

    class Meta:
        unique_together = ('project', 'user')


class ResearchProjectCollectionManager(models.Manager):
    """Manager for :class:`ResearchProjectCollection` model.

    This manager contains additional logic used by DRF serializers like
    details/update/delete urls
    """
    url_delete = 'research:project_collection_delete'

    def get_accessible(self, user=None, base_queryset=None, role_levels=None):
        """Return all :class:`ResearchProjectCollection` instances that given
        user has access to.

        :param user: if not none then that user will be used to filter
            accessible research project collections.
        :param base_queryset: queryset used to limit checked research projects
            collections. By default it's all collections.

        :return: research projects collections queryset
        """
        user = user or get_current_user()
        public = CollectionStatus.PUBLIC

        if role_levels is None:
            role_levels = [CollectionMemberLevels.ACCESS]

        if base_queryset is None:
            queryset = self.get_queryset()
        else:
            queryset = base_queryset

        if not user.is_authenticated():
            return queryset.filter(collection__status=public)
        return queryset.filter(
            Q(collection__owner=user) |
            Q(collection__managers=user) |
            Q(collection__status=public) |
            (
                Q(collection__members=user) &
                Q(
                    collection__members__collectionmember__level__in=role_levels
                )
            )
        ).distinct()

    def api_delete_context(self, item, user):
        """
        Method used in DRF api to return delete url if user has permissions
        """
        context = None
        if item.project.can_update(user):
            context = reverse(self.url_delete, kwargs={'pk': item.pk})
        return context


class ResearchProjectCollection(models.Model):
    """Many-To-Many model for ResearchProject <-> Collection relationship."""

    project = models.ForeignKey(ResearchProject)
    collection = models.ForeignKey('storage.Collection')

    objects = ResearchProjectCollectionManager()

    class Meta:
        ordering = ['collection__name',]

    def __unicode__(self):
        return unicode(self.collection.name)

    def can_delete(self, user=None):
        """
        ResearchProjectCollection can be removed when user has
        permissions to change ResearchProject
        """
        user = user or get_current_user()
        return self.project.can_update(user=user)

    def can_view(self, user=None):
        """
        ResearchProjectCollection can be accessed when user has
        permissions to change ResearchProject
        """
        user = user or get_current_user()
        return self.project.can_update(user=user)


@receiver(post_save, sender=ResearchProjectRole)
def project_role_collections_access_grant(sender, instance, **kwargs):
    """
    """
    from trapper.apps.storage.models import collections_access_grant
    user = instance.user

    if not ResearchProjectRole.objects.filter(
            project__pk=instance.project_id,
            user=user
    ).exclude(
            pk=instance.pk
    ).exclude(
        user__pk=instance.project.owner_id
    ).exists():
        collections = instance.project.collections.all()

        collections_access_grant(
            users=[user],
            collections=collections,
            level=CollectionMemberLevels.ACCESS
        )


@receiver(post_delete, sender=ResearchProjectRole)
def project_role_collections_access_revoke(sender, instance, **kwargs):
    """
    """
    from trapper.apps.storage.models import collections_access_revoke
    user = instance.user
    if not ResearchProjectRole.objects.filter(
            project__pk=instance.project_id,
            user=user
    ).exclude(
            pk=instance.pk
    ).exclude(
            user__id=instance.project.owner_id
    ).exists():
        collection_pks = instance.project.collections.values_list(
            'pk', flat=True
        )

        collections_access_revoke(
            collection_pks=collection_pks,
            user_pks=[user.pk],
            rproject=True,
            level=CollectionMemberLevels.ACCESS
        )


@receiver(post_save, sender=ResearchProjectCollection)
def project_collections_access_grant(sender, instance, **kwargs):
    """
    Signal used to grant an access to collections that belong to the
    research project for users that are a part of this project.
    """
    if kwargs['created']:
        from trapper.apps.storage.models import collections_access_grant
        roles = ResearchProjectRole.objects.filter(
            project=instance.project
        ).exclude(
            user=instance.project.owner
        ).prefetch_related('user')
        users = set([item.user for item in roles])

        collections_access_grant(
            users=users,
            collections=[instance.collection,],
            level=CollectionMemberLevels.ACCESS
        )


@receiver(post_delete, sender=ResearchProjectCollection)
def project_collections_access_revoke(sender, instance, **kwargs):
    """
    Signal used to revoke an access to collections that belong to the
    research project for users that are not a part of this project
    anymore.
    """
    from trapper.apps.storage.models import collections_access_revoke
    user_pks = ResearchProjectRole.objects.filter(
        project=instance.project
    ).exclude(
        user=instance.project.owner
    ).values_list('user__pk', flat=True)

    collections_access_revoke(
        user_pks=user_pks,
        collection_pks=[instance.collection.pk,],
        rproject=True,
        level=CollectionMemberLevels.ACCESS
    )

@receiver(pre_save, sender=ResearchProject)
def project_activated_notifiction(sender, instance, **kwargs):
    """When a research project is activated a user is notified by mail"""
    if not settings.EMAIL_NOTIFICATIONS:
        return 1
    try:
        old_instance = ResearchProject.objects.get(pk=instance.pk)
    except ResearchProject.DoesNotExist:
        pass
    else:
        if (
            old_instance.status in [False, None] and instance.status is True
        ):
            request = get_current_request()
            # send an email notification to a user that a research project has been activated
            send_mail(
                subject='Your Trapper research project has just been activated!',
                message=(
                    'Dear {username},\n\n'
                    'We are pleased to inform you that we have activated your research project:\n'
                    '{project_url}\n'
                    'Now you can start adding the collections of data to your project.\n\n'
                    'Best regards,\n'
                    'Trapper Team'
                ).format(
                    username=instance.owner.username.capitalize(),
                    project_url=request.build_absolute_uri(
                        reverse(
                            'research:project_detail', kwargs={'pk': instance.pk}
                        )
                    )
                ),
                from_email=None,
                recipient_list=[instance.owner.email],
                fail_silently=True
            )
