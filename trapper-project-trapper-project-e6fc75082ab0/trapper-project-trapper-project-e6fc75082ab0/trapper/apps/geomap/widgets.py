# -*- coding:utf-8 -*-

from django.forms import Select
from django.utils.safestring import mark_safe
from django.contrib.gis import admin
from django.forms.widgets import Widget
from django.utils.encoding import force_text
from django.forms.utils import flatatt
from django.utils.html import format_html


class TrapperOSMGeoAdmin(admin.OSMGeoAdmin):
    map_template = 'geomap/admin/osm.html'
    display_srid = 4326


class ButtonHiddenWidget(Widget):
    input_type = "hidden"

    def render(self, name, value, attrs=None):
        if value is None:
            value = u''
        final_attrs = self.build_attrs(attrs, type=self.input_type, name=name)
        icon = final_attrs.pop("icon", "glyphicon-unchecked")
        if value != u'':
            final_attrs['value'] = force_text(value)
        button_id = final_attrs.get("id", u"")
        if button_id != u'':
            button_id += u"_btn"
        btn = u'''<button id="{0}"" type="button" class="btn btn-default">
        <span class="glyphicon {1}"></span>
        </button>'''
        btn = btn.format(button_id, icon)
        return format_html(btn+u'<input{0} />', flatatt(final_attrs))


class LocationSelect(Select):

    def __init__(self, attrs=None, choices=()):
        super(LocationSelect, self).__init__(attrs=attrs, choices=choices)
        self.extra_option_params = {}
        if 'class' in self.attrs:
            self.attrs['class'] += u' select2-default'
        else:
            self.attrs['class'] = u'select2-default'

    def render(self, name, value, attrs=None, choices=()):
        if self.choices:
            queryset = getattr(self.choices, 'queryset')
            if queryset:
                queryset_values = queryset.values_list(
                    'pk', 'location_id', 'coordinates'
                )
                self.extra_option_params = dict(
                    [(item[0], item[1:]) for item in queryset_values]
                )

        if value is None:
            value = u''
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html(u'<select{0}>', flatatt(final_attrs))]
        options = self.render_options(choices, [value])

        if options:
            output.append(options)
        output.append(u'</select>')
        return mark_safe(u'\n'.join(output))

    def render_option(self, selected_choices, option_value, option_label):
        extra_option = u''
        params = self.extra_option_params.get(option_value, None)
        if params:
            location_id, point = params
            extra_option = mark_safe((
                u' data-longitude="{lng}" '
                u'data-latitude="{lat}" '
                u'data-location-id="{loc_id}"'
            ).format(
                lng=point.x,
                lat=point.y,
                loc_id=location_id
            ))
        option_value = force_text(option_value)

        if option_value in selected_choices:
            selected_html = mark_safe(u' selected="selected"')
            if not self.allow_multiple_selected:
                # Only allow for a single selection.
                selected_choices.remove(option_value)
        else:
            selected_html = u''

        return format_html(u'<option value="{0}"{1}{2}>{3}</option>',
                           option_value,
                           selected_html,
                           extra_option,
                           force_text(option_label))
