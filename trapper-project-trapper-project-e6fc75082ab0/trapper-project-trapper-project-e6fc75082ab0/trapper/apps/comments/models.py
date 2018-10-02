# -*- coding: utf-8 -*-
"""
Module contains model definition to store comments in various applications.
Relation to other models is defined as generic foreign key
"""
from __future__ import unicode_literals

from django.conf import settings
from django.utils.encoding import force_text
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from django.utils import timezone

from mptt.models import MPTTModel, TreeForeignKey

from trapper.middleware import get_current_user
from trapper.apps.common.fields import SafeTextField


COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)


class UserCommentManager(models.Manager):
    """Add custom methods to :class:`UserComment` model such as filtering
    comments only to specific model"""

    def for_model(self, model):
        """
        QuerySet for all comments for a particular model (either an instance or
        a class).
        """
        content_type = ContentType.objects.get_for_model(model)
        queryset = self.get_queryset().filter(content_type=content_type)
        if isinstance(model, models.Model):
            queryset = queryset.filter(
                object_pk=force_text(model._get_pk_val())
            )
        return queryset


class UserComment(MPTTModel):
    """
    An abstract base class that any custom comment models probably should
    subclass.
    """

    # Content-object field
    content_type = models.ForeignKey(
        ContentType,
        related_name="content_type_set_for_%(class)s"
    )
    object_pk = models.TextField()
    content_object = GenericForeignKey(
        ct_field="content_type", fk_field="object_pk"
    )
    parent = TreeForeignKey(
        'self', null=True, blank=True, related_name='children'
    )

    class MPTTMeta:
        order_insertion_by = ['content_type', 'object_pk']

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, related_name="%(class)s_comments"
    )
    comment = SafeTextField(max_length=COMMENT_MAX_LENGTH)

    # Metadata about the comment
    submit_date = models.DateTimeField(blank=True, editable=False)
    is_removed = models.BooleanField(default=False, editable=False)
    removed_date = models.DateTimeField(blank=True, null=True, editable=False)
    removed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', blank=True, null=True, editable=False
    )

    # Manager
    objects = UserCommentManager()

    class Meta:
        ordering = ('submit_date',)

    def __unicode__(self):
        return self.comment[:50]

    def save(self, *args, **kwargs):
        """Before saving comment user that posted comment has to be determined.
        This is done by using threadlocals that can store request or user
        connected to request.

        Also if submit date is not specified, it's set to current datetime
        """

        user = get_current_user()
        if not self.pk and self.user is None and user.is_authenticated():
            self.user = user

        if self.submit_date is None:
            self.submit_date = timezone.now()

        super(UserComment, self).save(*args, **kwargs)
