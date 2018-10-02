# -*- coding: utf-8 -*-
"""Model definitions or utils that can be used in other parts of project"""

from django.db import models
from django.conf import settings


class BaseAccessMember(models.Model):
    """Abstract model that hold user and created date field, that can
    be used in various applications

    This model adds:

    * `user` - foreign key to :class:`auth.User`
    * `date_created` - :class:`models.DateTimeField` with default value set to
        :func:`datetime.datetime.now`
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    date_created = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        abstract = True
