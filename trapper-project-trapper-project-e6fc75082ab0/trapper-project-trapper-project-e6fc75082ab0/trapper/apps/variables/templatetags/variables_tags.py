# -*- coding: utf-8 -*-
"""
Templatetags used to retrieve values from database directly from template
"""

from django import template

from trapper.apps.variables.models import Variable

register = template.Library()


@register.simple_tag(takes_context=True, name='get_variable')
def get_variable(context, namespace, name, **kwargs):
    """Return value from database by given `namespace` and `name`"""
    return Variable.get(namespace=namespace, name=name, default=u'')
