# -*- coding: utf-8 -*-
"""Forms related to Messaging application"""
from __future__ import unicode_literals

from django import forms
from django.contrib.auth import get_user_model

from trapper.apps.messaging.models import Message

User = get_user_model()


class MessageForm(forms.ModelForm):
    """Message form that is used for creating messages to other users.
    This form exclude currently logged in user from list of
    recipients.
    Also sending messages to inactive users is not allowed
    """

    class Meta:
        model = Message
        fields = ['subject', 'text', 'user_to']

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super(MessageForm, self).__init__(*args, **kwargs)
        # exclude inactive users and current user
        user_to_field = self.fields['user_to']
        user_to_field.queryset = User.objects.filter(
            is_active=True
        ).exclude(pk=request.user.pk)
        # select2 classing
        user_to_field.widget.attrs['class'] = 'form-control select2-default'
