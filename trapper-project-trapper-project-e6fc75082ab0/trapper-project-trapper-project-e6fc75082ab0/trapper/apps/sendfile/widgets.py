# -*- coding: utf-8 -*-

from django.core.urlresolvers import reverse
from django.forms.fields import ClearableFileInput
from django.utils.html import escape, conditional_escape
from django.utils.encoding import force_unicode
from django.utils.safestring import mark_safe
from django.forms.widgets import CheckboxInput

from django.contrib.admin.widgets import AdminFileWidget

__all__ = ['SendFileFileInput']


class SendFileFileInput(AdminFileWidget, ClearableFileInput):
    def render(self, name, value, attrs=None):
        substitutions = {
            'initial_text': self.initial_text,
            'input_text': self.input_text,
            'clear_template': '',
            'clear_checkbox_label': self.clear_checkbox_label,
        }
        template = u'%(input)s'
        substitutions['input'] = super(
            ClearableFileInput, self
        ).render(name, value, attrs)

        if value and hasattr(value, "name"):
            template = self.template_with_initial
            substitutions['initial'] = (
                u'<a href="{admin_url}?file={file_url}">{label}</a>'.format(
                    admin_url=reverse('sendfile:sendfile_direct_serve'),
                    file_url=escape(value.name),
                    label=escape(force_unicode(value))
                )
            )
            if not self.is_required:
                checkbox_name = self.clear_checkbox_name(name)
                checkbox_id = self.clear_checkbox_id(checkbox_name)
                substitutions['clear_checkbox_name'] = conditional_escape(
                    checkbox_name
                )
                substitutions['clear_checkbox_id'] = conditional_escape(
                    checkbox_id
                )
                substitutions['clear'] = CheckboxInput().render(
                    checkbox_name, False, attrs={'id': checkbox_id}
                )
                substitutions['clear_template'] = \
                    self.template_with_clear % substitutions

        return mark_safe(template % substitutions)
