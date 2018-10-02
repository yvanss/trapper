# -*- coding: utf-8 -*-
"""
Module contains model definition to work with messages.

.. note::
    Messages use hashed keys so they are harder to guess.

.. note::
    Messages application contains models responsible for
    managing access requests for :class:`storage.models.Resource` and
    :class:`storage.models.Collection`

"""
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.timezone import now

from trapper.middleware import get_current_user
from trapper.apps.common.utils.identity import create_hashcode
from trapper.apps.common.fields import SafeTextField
from trapper.apps.messaging.taxonomies import MessageType, MessageApproveStatus


class Message(models.Model):
    """E-mail like messaging features among the users.

    Instead of using integer based primary key - hashcode is used, which is
    harder to guess in url
    """

    hashcode = models.CharField(
        max_length=64, verbose_name=u"Hashcode",
        editable=False, default=create_hashcode,
        help_text=u"Unique hash used to get message"
    )

    subject = models.CharField(max_length=255, verbose_name=u"Message subject")
    text = SafeTextField(max_length=1000, verbose_name=u"Message body")
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages')
    user_to = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='received_messages')
    date_sent = models.DateTimeField(auto_now_add=True)
    date_received = models.DateTimeField(blank=True, null=True)

    message_type = models.PositiveIntegerField(
        choices=MessageType.CHOICES, default=MessageType.STANDARD
    )

    class Meta:
        ordering = ['-date_sent']

    def mark_received(self, user):
        """Mark message as viewed by updating received date"""
        if self.is_new() and self.user_to == user:
            self.date_received = now()
            self.save()
        return self

    def __unicode__(self):
        return unicode(
            "%s -> %s (sent: %s)" % (
                self.user_from, self.user_to, self.date_sent)
        )

    def is_new(self):
        """Check if message is new or already viewed"""
        return not bool(self.date_received)

    def can_detail(self, user=None):
        """User can see details only if message is sent to him or by him"""
        user = user or get_current_user()
        return self.user_from == user or self.user_to == user

    @property
    def is_inbox(self):
        """Based on currently logged in user decide if message should marked
        as incomming message"""
        user = get_current_user()
        return (
            self.user_to == user and
            self.message_type not in [
                MessageType.COLLECTION_REQUEST,
            ]
        )

    @property
    def is_outbox(self):
        """Based on currently logged in user decide if message should marked
        as sent message"""
        user = get_current_user()
        return (
            self.user_to != user and
            self.message_type == MessageType.STANDARD
        )

    @property
    def is_collection_request(self):
        """Based on currently logged in user decide if message should marked
        as collection access request"""
        return self.message_type == MessageType.COLLECTION_REQUEST

    @property
    def is_request(self):
        """Check if message is request for access"""
        return self.message_type in [
            MessageType.COLLECTION_REQUEST,
        ]

    def get_absolute_url(self):
        return reverse(
            'messaging:message_detail',
            kwargs={'hashcode': self.hashcode}
        )


class BaseAccessRequestModel(models.Model):
    """
    Base class for handling different kind of access requests for example

    * requests for access to resources
    * requests for access to collections
    """

    name = models.CharField(max_length=255)
    added_at = models.DateTimeField(auto_now_add=True, editable=False)
    resolved_at = models.DateTimeField(blank=True, null=True)
    is_approved = models.NullBooleanField(
        blank=True, null=True, default=None,
        choices=MessageApproveStatus.CHOICES
    )
    message = models.ForeignKey(Message)

    def __unicode__(self):
        return unicode("%s (%s)" % (self.name, self.__class__.__name__))

    def resolve_notify(self, user):
        """Method used in subclass to notify user about request being
        resolved.

        This method doesn't rise NotImplementedError because some
        subclassess may not want to send any message"""
        pass

    def revoke_notify(self, user):
        """Method used in subclass to notify user about access being
        revoked.

        This method doesn't rise NotImplementedError because some
        subclassess may not want to send any message"""
        pass

    def approve(self, user):
        """Method called when request was accepted"""
        raise NotImplemented("This method has to be implemented in subclass")

    def revoke(self, user):
        """Method called when request was revoked"""
        raise NotImplemented("This method has to be implemented in subclass")

    def resolve_access(self, user, is_approved=False):
        """Resolve request by:

        * mark request resolved date
        * set resolve status
        * mark message as read
        * if request is approved call approve method from subclass
        """
        self.is_approved = is_approved
        self.resolved_at = now()
        self.message.mark_received(user=user)
        self.save()
        self.resolve_notify(user)

        if is_approved:
            self.approve(user=user)

    def resolve_revoke(self, user):
        """Default actions that are taken when access to object has been
        revoked

        By default `is_approved` is set to `False`, notification is
        sent to user and :func:`revoke` method is called from subclassed
        model
        """
        self.is_approved = False
        self.save()
        self.revoke_notify(user=user)
        self.revoke(user=user)

    class Meta:
        abstract = True
        ordering = ('-added_at', '-resolved_at')


class CollectionRequest(BaseAccessRequestModel):
    """
    Notification about an incoming collection request
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='collection_requests')
    user_from = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='my_collection_requests')
    project = models.ForeignKey('research.ResearchProject')
    collections = models.ManyToManyField(
        'storage.Collection', blank=True, related_name='collection_request'
    )

    def resolve_notify(self, user):
        names = ", ".join(
            self.collections.values_list('name', flat=True)
        )

        Message.objects.create(
            subject='Decision on your request for collections'.format(
                names=names,
                status=self.get_is_approved_display()
            ),
            text=(
                'You have recently requested for the access to '
                '<a href="{url}">these collections</a>. '
                'Their owner decided that your request is: '
                '<strong>{status}</status>.'
            ).format(
                url=self.message.get_absolute_url(),
                title=self.message.subject,
                status=self.get_is_approved_display()
            ),
            user_from=user,
            user_to=self.message.user_from,
            date_sent=now(),
            message_type=MessageType.STANDARD
        )

    def approve(self, user):
        """
        Each requested collection is registered in CollectionMember model with
        ACCESS level which allows to use collection in requested project
        """
        from trapper.apps.storage.models import collections_access_grant
        collections = self.collections.all()
        users = [self.user_from,]
        collections_access_grant(collections, users, level=5)

    def revoke_notify(self, user):
        """Notify user that access for :class:`trapper.apps.storage.Collection`
        has been revoked"""
        names = ", ".join(
            self.collections.values_list('name', flat=True)
        )

        Message.objects.create(
            subject='Revoked access to collections',
            text=(
                'We are regret to inform you that your permission to access '
                'the following collections has been revoked by their owner:<br>'
                '<strong>{names}</strong>.'
            ).format(
                names=names
            ),
            user_from=user,
            user_to=self.message.user_from,
            date_sent=now(),
            message_type=MessageType.STANDARD
        )

    def revoke(self, user):
        """
        """
        from trapper.apps.storage.models import collections_access_revoke
        collections = self.collections.all()
        users = [self.user_from.pk,]
        collections_access_revoke(collections, users, level=5)
