# -*- coding: utf-8 -*-
"""
Form used to create new comment or reply
"""
from __future__ import unicode_literals

from django.forms import widgets

from crispy_forms.layout import Layout, Fieldset

from trapper.apps.common.forms import BaseCrispyModelForm
from trapper.apps.comments.models import UserComment


class UserCommentForm(BaseCrispyModelForm):
    """This form is used within templatetag to be rendered directly in
    template. Thanks to that, there is no need to modify views logic
    to use comments application"""

    def get_layout(self):
        """Define layout for crispy form helper"""
        return Layout(
            Fieldset(
                '',
                'comment',
                'content_type',
                'object_pk',
                'parent'
            ),
        )

    class Meta:
        model = UserComment
        fields = '__all__'
        widgets = {
            'parent': widgets.HiddenInput(),
            'content_type': widgets.HiddenInput(),
            'object_pk': widgets.HiddenInput()
        }
