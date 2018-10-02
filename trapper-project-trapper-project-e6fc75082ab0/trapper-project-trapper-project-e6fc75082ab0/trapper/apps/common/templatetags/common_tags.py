# -*- coding: utf-8 -*-
"""Module containing commonly used templatetags"""

from django import template
from django.conf import settings
from django.forms import forms
from django.template import Context
from django.template.loader import get_template

from crispy_forms.templatetags.crispy_forms_filters import TEMPLATE_PACK
from crispy_forms.exceptions import CrispyError

register = template.Library()


@register.simple_tag(takes_context=True)
def nav_active(context, menu):
    """Templatetag used to mark active given menu by adding proper
    CSS class"""
    context[menu] = ' active active-icon'
    return ""


@register.filter(name='as_crispy_non_label_field')
def as_crispy_non_label_field(field, template_pack=TEMPLATE_PACK):
    """
    Renders a form field like a django-crispy-forms field::

        {% load common_tags %}
        {{ form.field|as_crispy_non_label_field }}

    or::

        {{ form.field|as_crispy_non_label_field:"bootstrap" }}

    .. note::
        This method is variation of original as_crispy_field but it has
        labels hidden which original version won't support
    """
    if not isinstance(field, forms.BoundField) and settings.DEBUG:
        raise CrispyError(
            '|as_crispy_field got passed an invalid or inexistent field'
        )

    output_template = get_template('%s/field.html' % template_pack)
    context = Context(
        {'field': field, 'form_show_errors': True, 'form_show_labels': False}
    )
    return output_template.render(context)


@register.filter
def get_range(value, start=0):
    """
    Filter - returns a list containing range made from given value
    Usage (in template):

    <ul>{% for i in 3|get_range %}
      <li>{{ i }}. Do something</li>
    {% endfor %}</ul>

    Results with the HTML:
    <ul>
      <li>0. Do something</li>
      <li>1. Do something</li>
      <li>2. Do something</li>
    </ul>

    Instead of 3 one may use the variable set in the views
    """
    return range(start, value)
