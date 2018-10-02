# -*- coding: utf-8 -*-
"""
Module contains models related to user profile.
When User instance is created, then UserProfile instance is created by
default.

For registration django-allauth is used, but account is not activated.
Instad of mail is sent to admins, so they can activate account
(activation sends email to user).

"""
from __future__ import unicode_literals

import os

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.urlresolvers import reverse
from  django.core.files.storage import FileSystemStorage
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.utils.timezone import now

from trapper.apps.common.fields import ResizedImageField, SafeTextField
from trapper.apps.messaging.taxonomies import MessageType
from trapper.apps.common.utils.models import delete_old_file
from trapper.apps.common.fields import SafeTextField
from trapper.apps.accounts.utils import (
    get_pretty_username, create_external_media,
    get_external_data_packages_path
)
from trapper.apps.accounts.taxonomy import PackageType, ExternalStorageSettings


class User(AbstractUser):
    class Meta:
        db_table = 'auth_user'


class UserProfile(models.Model):
    """
    Base profile model used to store additional details like avatar,
    some about me description and institution
    """

    user = models.OneToOneField(User)
    avatar = ResizedImageField(
        upload_to='avatars', blank=True, null=True,
        max_width=80, max_height=80
    )
    about_me = SafeTextField(blank=True, null=True)
    institution = models.CharField(max_length=255, blank=True, null=True)
    system_notifications = models.BooleanField(
        default=True, help_text=(
            'Do you want to receive emails with system notifications?'
        )
    )

    def __unicode__(self):
        """By default printing profile should display pretty version
        of username"""
        return get_pretty_username(user=self.user)

    def get_absolute_url(self):
        """Return absolute url to user profile"""
        return reverse(
            'accounts:show_profile', kwargs={'username': self.user.username}
        )

    @property
    def avatar_url(self):
        """Return user avatar or default one"""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        else:
            return '{url}accounts/img/avatar.png'.format(
                url=settings.STATIC_URL
            )

    def has_unread_messages(self):
        """Checks whether user has any unread messages
        (see :class:`trapper.apps.messaging.models.Message`).
        """

        return self.user.received_messages.filter(
            date_received=None
        ).exclude(
            message_type__in=[
                MessageType.COLLECTION_REQUEST,
                MessageType.RESOURCE_REQUEST
            ]
        ).exists()

    def count_unread_messages(self):
        """Returns the number of unread messages.
        (see :class:`trapper.apps.messaging.models.Message`).
        """

        return self.user.received_messages.filter(
            date_received=None
        ).exclude(
            message_type__in=[
                MessageType.COLLECTION_REQUEST,
                MessageType.RESOURCE_REQUEST
            ]
        ).count()

    def count_inbox_messages(self):
        """Returns total number of inbox messages.
        (see :class:`trapper.apps.messaging.models.Message`).
        """

        return self.user.received_messages.exclude(
            message_type=MessageType.COLLECTION_REQUEST
        ).count()

    def awaiting_collection_requests(self):
        """Returns the number of collections requests that has not been
        resolved yet.
        This means that some users asked for access to collection
        """

        return self.user.collection_requests.filter(
            resolved_at__isnull=True
        ).count()

    def awaiting_resource_requests(self):
        """Returns the number of resource requests that has not been
        resolved yet.
        This means that some users asked for access to resources
        """

        return self.user.resource_requests.filter(
            resolved_at__isnull=True
        ).count()

    # def can_rate(self, resource):
    #     return
    #     # return True

    def save(self, **kwargs):
        """Delete changed files before save new instance"""
        delete_old_file(self, 'avatar')
        super(UserProfile, self).save(**kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """When new user is created - create default profile"""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(pre_save, sender=User)
def active_notifiction(sender, instance, **kwargs):
    """When a user account becomes active a user is notified by mail"""
    if not settings.EMAIL_NOTIFICATIONS:
        return 1
    try:
        old_instance = User.objects.get(pk=instance.pk)
    except User.DoesNotExist:
        pass
    else:
        if (
            old_instance.is_active is False and instance.is_active is True
        ):
            # Ensure that the external media directory exists
            create_external_media(username=instance.username)

            # send an email notification to a user that account has been activated
            send_mail(
                subject='Your Trapper account has just been activated!',
                message=(
                    'Dear {username},\n\n'
                    'We activated your account. Now you can login to Trapper.\n\n'
                    'Best regards,\n'
                    'Trapper Team'
                ).format(username=instance.username.capitalize()),
                from_email=None,
                recipient_list=[instance.email],
                fail_silently=True
            )


class UserTask(models.Model):
    """
    Helper model to save information about user's celery tasks
    """

    user = models.ForeignKey(User)
    task_id = models.CharField(max_length=765, unique=True)


external_media_location = FileSystemStorage(
    location=settings.EXTERNAL_MEDIA_ROOT,
    base_url=settings.EXTERNAL_MEDIA_URL
)

def user_data_package_upload_to(instance, filename):
    return os.path.join(
        instance.user.username,
        ExternalStorageSettings.DATA_PACKAGES, filename
    )

class UserDataPackage(models.Model):
    """
    """
    user = models.ForeignKey(User)
    package = models.FileField(
        storage=external_media_location,
        upload_to=user_data_package_upload_to
    )
    package_type = models.CharField(
        choices=PackageType.CHOICES, max_length=1, null=True, blank=True
    )
    date_created = models.DateTimeField(null=True, blank=True, default=now)
    description = SafeTextField(
        blank=True, null=True
    )

    def filename(self):
        return os.path.basename(self.package.name)

    def can_delete(self, user):
        return self.user == user

    def delete(self, *args, **kwargs):
        self.package.delete()
        super(UserDataPackage, self).delete(*args, **kwargs)

    def get_download_url(self):
        return reverse(
            'accounts:data_package_sendfile_media',
            kwargs={'pk': self.pk}
        )

    
