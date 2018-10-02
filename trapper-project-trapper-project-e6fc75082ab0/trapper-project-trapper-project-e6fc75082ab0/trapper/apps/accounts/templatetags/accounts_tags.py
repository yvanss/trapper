# -*- coding: utf-8 -*-
"""
Helpers used in templates or in views for better managing
User or UserProfile model instances
"""


from django import template
from trapper.apps.accounts.utils import get_pretty_username


register = template.Library()


@register.simple_tag(takes_context=False)
def pretty_username(user):
    """This templatetag is used because data is stored on User model
    and it's more efficient way than going through UserProfile

    :param user: User model instance
    :return: prettyfied version of username
    """
    return get_pretty_username(user=user)


@register.filter(name='pretty_username')
def pretty_username_filter(user):
    """
    Filter version of pretty_username templatetag

    :param user: User model instance
    :return: prettyfied version of username
    """
    return get_pretty_username(user=user)
