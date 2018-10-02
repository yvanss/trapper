# -*- coding: utf-8 -*-
"""Widget and field used by
:class:`apps.media_classification.models.Classification`  and
:class:`apps.media_classification.models.Classificattor` models for
video time range selection
"""
import time

from django import forms
from django.forms import widgets
from django.utils.html import mark_safe
from django.core.exceptions import ValidationError


class VideoTimeRangeWidget(widgets.MultiWidget):
    """
    This widget should be used together with:
    1) http://www.videojs.com/
    2) https://github.com/danielcebrian/rangeslider-videojs
    This widget uses bootstrap 3.0 to style ui elements.
    The following javascript functions must be implemented to use this widget
    correctly:
    1) setValues(targetPlayer)
    2) getValues(targetPlayer)
    3) playLoop(targetPlayer)
    """

    def __init__(self, time_format='%H:%M:%S', attrs=None):
        attrs = attrs or {}
        self.time_format = time_format
        _widgets = (
            widgets.TimeInput(
                {'placeholder': 'Video start'}, format=time_format
            ),
            widgets.TimeInput(
                {'placeholder': 'Video end'}, format=time_format
            ),
        )
        super(VideoTimeRangeWidget, self).__init__(_widgets, attrs)
        self.css_classes = 'form-annotation'

    def decompress(self, values_list):
        """Convert values to python list"""
        if values_list:
            return values_list
        return [None, None]

    def value_from_datadict(self, data, files, name):
        """Create unique name for each widget"""
        values_list = [
            widget.value_from_datadict(data, files, name + '_%s' % i)
            for i, widget in enumerate(self.widgets)]
        return values_list

    def render(self, name, value, attrs=None):
        """Render widget logic"""
        # HTML to be added to the output
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # value is a list of values, each corresponding to a widget in
        # self.widgets
        if not isinstance(value, list):
            value = self.decompress(value)

        output = [
            '<div class="form-annotation">',
            '<div class="input-group">'
        ]
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)

        # Widgets starts from 0
        widgets_count = len(self.widgets) - 1
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
                final_attrs['class'] = \
                    'timeinput form-control timeinput-annotations'
            output.append(
                widget.render(name + '_%s' % i, widget_value, final_attrs)
            )
            if i < widgets_count:
                output.append((
                    '<span class="input-group-addon">'
                    '<span class="fa fa-clock-o"></span></span>'
                ))

        output.append('</div>')
        if 'disabled' not in self.attrs:
            output.append((
                '<div class="btn-group">'
                '<button class="btn btn-success btn-get">get</button>'
                '<button class="btn btn-default btn-play">'
                '   <span class="fa fa-play"></span>'
                '</button>'
                '<button class="btn btn-danger btn-set">set</button>'
                '</div>'
            ))
        output.append('</div>')

        return mark_safe(self.format_output(output))


class VideoTimeRangeField(forms.MultiValueField):
    """Multivaluefield for storing time start and time end in database
    This field uses :class:`VideoTimeRangeWidget` widget
    """
    widget = VideoTimeRangeWidget
    is_annotation = True

    def __init__(self, *args, **kwargs):
        """Define fields as :class:`forms.CharField`"""
        fields = (forms.CharField(), forms.CharField())
        super(VideoTimeRangeField, self).__init__(fields, *args, **kwargs)

    def compress(self, values_list):
        """Convert values to time using defined in widget time format"""
        try:
            # do this to check if widgets collected data of expected format
            # which is -> [time,time]
            [time.strptime(v, self.widget.time_format) for v in values_list]
        except ValueError:
            raise ValidationError(
                'Wrong format. Use: %s' % self.widget.time_format
            )
        return values_list
