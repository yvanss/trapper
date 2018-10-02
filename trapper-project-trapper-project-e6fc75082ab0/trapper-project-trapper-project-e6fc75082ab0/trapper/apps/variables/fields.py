# -*- coding: utf-8 -*-
"""Field definitions to store custom various values in database"""

import cPickle
import base64

from django.db import models


class ObjectField(models.TextField):
    """Field used to store serialized data in database"""

    #__metaclass__ = models.SubfieldBase

    def _dumps(self, value):
        """Convert value into format that could be store in database"""
        return "OBJ:" + base64.urlsafe_b64encode(cPickle.dumps(value))

    def _loads(self, value):
        """Convert stored value from serialized version into original
        type"""
        return cPickle.loads(base64.urlsafe_b64decode(str(value[4:])))

    def get_prep_value(self, value):
        """Safe picklev value before storing in database"""
        return self._dumps(value)

    def from_db_value(self, value, *args, **kwargs):
        return self.to_python(value)

    def to_python(self, value):
        """For strings that were converted using :func:`_dumps` restore
        their original structure"""
        if isinstance(value, basestring) and value.startswith("OBJ:"):
            return self._loads(value)
        return value

    def value_to_string(self, obj):
        """Convert object into string"""
        value = self._get_val_from_obj(obj)
        return self._dumps(value)
