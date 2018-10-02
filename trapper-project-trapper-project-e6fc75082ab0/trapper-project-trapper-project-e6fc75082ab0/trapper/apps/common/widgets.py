# -*- coding: utf-8 -*-
"""Widgets used in various applications"""

from django.forms.widgets import TextInput


class DisabledTextInput(TextInput):
    """Disabled textinput widget"""

    def __init__(self, **kwargs):
        super(DisabledTextInput, self).__init__(**kwargs)
        self.attrs['disabled'] = True
        self.attrs['readonly'] = True
