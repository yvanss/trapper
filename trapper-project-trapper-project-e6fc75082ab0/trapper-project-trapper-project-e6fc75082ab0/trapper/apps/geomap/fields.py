# -*- coding:utf-8 -*-

from django.forms import ModelChoiceField, ChoiceField
from trapper.apps.geomap.widgets import LocationSelect


class LocationChoiceField(ChoiceField):
    widget = LocationSelect


class LocationModelChoiceField(ModelChoiceField):
    widget = LocationSelect
