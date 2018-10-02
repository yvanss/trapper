# -*- coding: utf-8 -*-
"""
Module contains model definition to work with variables stored in database.
"""

from django.db import models
from django.utils.translation import ugettext_lazy as _

from fields import ObjectField


class Variable(models.Model):
    """Model used to store custom values in database"""
    UNDEFINED = object()

    class Meta:
        verbose_name = _(u"Variable")
        verbose_name_plural = _(u"Variables")
        ordering = ('namespace', 'name')
        unique_together = (('namespace', 'name'),)

    namespace = models.CharField(verbose_name=_(u"Namespace"), max_length=127)
    name = models.CharField(verbose_name=_(u"Name"), max_length=127)
    value = ObjectField(verbose_name=_(u"Value"))

    @classmethod
    def get(cls, namespace, name, default=UNDEFINED):
        """Method used to retrieve value from database"""
        try:
            val = cls.objects.get(namespace=namespace, name=name)
        except cls.DoesNotExist:
            if default is cls.UNDEFINED:
                raise
            else:
                return default
        else:
            return val.value

    @classmethod
    def set(cls, namespace, name, value):
        """Method used to store value in database"""
        val, created = cls.objects.get_or_create(
            namespace=namespace, name=name, defaults={'value': value}
        )
        if not created:
            val.value = value
            val.save()

    def __unicode__(self):
        return u"%s.%s = %s" % (self.namespace, self.name, self.value)
