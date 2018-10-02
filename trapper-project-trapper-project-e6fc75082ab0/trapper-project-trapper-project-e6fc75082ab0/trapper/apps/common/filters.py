# -*- coding: utf-8 -*-
"""Commonly used filters"""

import json
import datetime
import re
import six
import operator
import django_filters
from rest_framework.filters import SearchFilter

from django.conf import settings
from django.db.models import Q
from django import forms
from django.utils import timezone

from trapper.middleware import get_current_user
from trapper.apps.common.tools import parse_pks


class BaseOwnBooleanFilter(django_filters.Filter):
    """Base boolean filter class for limiting queryset to values that are
    owned by currently logged in user or user is in managers (optionally)
    or have a role in some project (optionally)"""
    field_class = forms.BooleanField
    status_class = None

    def __init__(
            self, owner_field='owner',
            managers=True, managers_field='managers',
            role_levels=None, role_field='project_roles',
            *args, **kwargs
    ):
        self.owner_field = owner_field
        self.managers = managers
        self.managers_field = managers_field
        self.role_levels = role_levels
        self.role_field = role_field
        super(BaseOwnBooleanFilter, self).__init__(*args, **kwargs)

    def filter(self, queryset, value):
        user = get_current_user()
        if not user.is_authenticated():
            return queryset
        if value is True:
            or_queries = [Q(**{self.owner_field:user}),]
            if self.managers:
                or_queries.append(
                    Q(**{self.managers_field:user})
                )
            if self.role_levels:
                or_queries.append(
                    Q(
                         **{'{role_field}__user'.format(
                            role_field=self.role_field):user}
                    ) &
                    Q(
                        **{'{role_field}__name__in'.format(
                            role_field=self.role_field):self.role_levels}
                    )
                )
            queryset = queryset.filter(reduce(operator.or_, or_queries))
        return queryset


class BaseDateFilter(django_filters.DateFilter):
    """Base date filter with custom input formats"""

    field_class = forms.DateField

    def __init__(self, *args, **kwargs):
        super(BaseDateFilter, self).__init__(*args, **kwargs)
        self.field.input_formats = settings.DATE_INPUT_FORMATS


class BaseTimeFilter(django_filters.Filter):
    """Base time filter compatible with a
    :class:`django.db.models.DateTimeField`."""

    field_class = forms.CharField

    def __init__(self, time_format, lookup_type, *args, **kwargs):
        super(BaseTimeFilter, self).__init__(*args, **kwargs)
        self.time_format = time_format
        self.lookup_type = lookup_type
        self.timezone = timezone.get_current_timezone()

    def filter(self, qs, value):
        if value:
            try:
                value = datetime.datetime.strptime(
                    value, self.time_format 
                ).time()
            except ValueError:
                return qs.none()
            # reduce 'datetime.datetime' to 'datetime.time';
            # produce tuples: (object.pk, datetime.time())
            objects = [
                (k[0], k[1].astimezone(
                    self.timezone).time()
             ) for k in qs.values_list(
                 'pk', self.name)
            ]
            if self.lookup_type == 'from':
                objects = [
                    k for k in objects if k[1] >= value
                ]
            if self.lookup_type == 'to':
                objects = [
                    k for k in objects if k[1] <= value
                ]
            if objects:
                return qs.filter(pk__in=zip(*objects)[0])
            else:
                return qs.none()
        return qs


class BaseLocationsMapFilter(django_filters.Filter):
    """Filters queryset based on locations set passed from
    the map view `/geomap/map`. Received locations are in a form of
    list of integers: `int1,int2,...,intN`"""

    def filter(self, qs, value):
        if value:
            pks = parse_pks(value)
            if pks:
                return qs.filter(**{
                    "{model_field}__in".format(
                        model_field=self.name
                    ): pks
                })
        return qs


class BaseFilterSet(django_filters.FilterSet):
    """Simple filter that makes possible to filter
    through pk that is list of integers: `int1,int2,...,intN`"""

    pk = django_filters.MethodFilter(action='filter_pks')

    def format_pks(self, pks):
        """Prepare list of pk from string"""
        return parse_pks(pks=pks)

    # def filter_pks(self, qs, value):
    #     """Filter queryset against given value"""
    #     # if value.strip() == "":
    #     #     return qs
    #     # pks = self.__class__._format_pks(value)
    #     # qs = qs.filter(pk__in=pks)
    #     return qs


# customized DRF SearchFilter backend
class RegExpSearchFilter(SearchFilter):

    def get_search_terms(self, request):
        """
        Search term is set by a ?search=... query parameter,
        and should be a valid regular expression term.
        """
        params = request.query_params.get(self.search_param, '')
        if not params:
            return ''
        try:
            re.compile(params)
            return params
        except re.error:
            return 1

    def construct_search(self, field_name):
        if field_name.startswith('='):
            return "%s__icontains" % field_name[1:]
        else:
            return "%s__iregex" % field_name

    def filter_queryset(self, request, queryset, view):
        search_fields = getattr(view, 'search_fields', None)

        if not search_fields:
            return queryset

        search_term = self.get_search_terms(request)
        if not search_term:
            return queryset
        elif search_term == 1:
            return queryset.none()
        else:
            orm_lookups = [self.construct_search(six.text_type(search_field))
                           for search_field in search_fields]
            or_queries = [Q(**{orm_lookup: search_term})
                          for orm_lookup in orm_lookups]
            queryset = queryset.filter(reduce(operator.or_, or_queries)).distinct()
            return queryset
