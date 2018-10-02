# -*- coding: utf-8 -*-
"""
Comments application is pluggable into another applications by using
templatetags.

This module contains three simple templatetags that makes comments usuable

* :func:`get_comment_form` that should be used for posting or replaying comments
* :func:`get_comments` that should be used to get comments
* :func:`get_comments_count` that return number of comments
"""

from django import template
from django.contrib.contenttypes.models import ContentType
from django.conf import settings

from trapper.apps.comments.forms import UserCommentForm
from trapper.apps.comments.models import UserComment

register = template.Library()


class CommentTag(object):
    """Container for comments logic"""
    context_object_name = 'object'

    def __init__(
            self, context, item=None, show_header=True, readonly=False
    ):
        self.context = context
        self.show_header = show_header
        self.readonly = readonly
        self.item = self.get_item(item=item)
        self.content_type = self.get_content_type()

    def get_item(self, item):
        """Item can be passed directly or can be 'guessed' from context"""
        if item is None:
            item = self.context.get(self.context_object_name, None)
        return item

    def get_content_type(self):
        """To get list of comments, it's necessary to get content type
        of items we want to return"""
        meta = getattr(self.item, '_meta')
        return ContentType.objects.get(
            model=meta.model_name,
            app_label=meta.app_label
        )

    def render_form(self):
        """Render comment form containing content type and item primary
        key that will be used to store comment"""
        initial = {
            'content_type': self.content_type.pk,
            'object_pk': self.item.pk
        }

        form = UserCommentForm(initial=initial)
        return {'form': form, 'show_header': self.show_header}

    def get_comments(self):
        """Get queryset with comments that belong to given item"""
        return UserComment.objects.filter(
            content_type=self.content_type,
            object_pk=self.item.pk
        )

    def render_comments(self):
        """Render list of structured comments"""
        return {
            'nodes': self.get_comments(),
            'show_header': self.show_header,
            'readonly': self.readonly,
            'STATIC_URL': settings.STATIC_URL,
        }

    def render_comments_count(self):
        """Return number of comments that belong to given item"""
        return self.get_comments().count()


@register.inclusion_tag('user_comments/form.html', takes_context=True)
def get_comment_form(context, item=None, show_header=True, readonly=False):
    """
    Templatetag that should be used to create or reply comments

    :param context: context instance from template
    :param item: instance of any model that will be used to limit comments
        to specific model. If no item is passed then templatetag will try
        to guess which model is used by looking into context for
        context_object_name, which by default is 'object'
    :param show_header: boolean value that determines if form should contain
        header. In some situations only form is needed
    :param readonly: boolean value that determines if form is displayed
        as readonly
    :return: rendered comment form
    """
    tag = CommentTag(
        context=context, item=item, show_header=show_header, readonly=readonly
    )
    return tag.render_form()


@register.inclusion_tag(
    'user_comments/comment_list.html', takes_context=True
)
def get_comments(context, item=None, show_header=True, readonly=False):
    """
    Templatetag that should be used to get list of comments related to given
    or guessed model.

    :param context: context instance from template
    :param item: instance of any model that will be used to limit comments
        to specific model. If no item is passed then templatetag will try
        to guess which model is used by looking into context for
        context_object_name, which by default is 'object'
    :param show_header: boolean value that determines if form should contain
        header. In some situations only form is needed
    :param readonly: boolean value that determines if form is displayed
        as readonly
    :return: rendered list of comments
    """
    tag = CommentTag(
        context=context, item=item, show_header=show_header, readonly=readonly
    )
    return tag.render_comments()


@register.simple_tag(takes_context=True)
def get_comments_count(context, item=None):
    """
    Templatetag that should be used to get number of comments related to given
    or guessed model

    :param context: context instance from template
    :param item: instance of any model that will be used to limit comments
        to specific model. If no item is passed then templatetag will try
        to guess which model is used by looking into context for
        context_object_name, which by default is 'object'

    :return number of comments
    """
    tag = CommentTag(context=context, item=item)
    return tag.render_comments_count()
