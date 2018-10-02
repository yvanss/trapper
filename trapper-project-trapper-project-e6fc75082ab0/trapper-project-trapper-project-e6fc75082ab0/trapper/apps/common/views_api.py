# -*- coding: utf-8 -*-
"""Views related to **Django Rest Framework** application that are used
in other applications to define REST API"""
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import pagination
from rest_framework.filters import DjangoFilterBackend
from rest_framework import renderers

from django.db.models import Q

from trapper.apps.common.filters import RegExpSearchFilter


class ListPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 500

    def get_paginated_response(self, data):
        return Response({
            'pagination': {
                'page': self.page.number,
                'page_size': self.page.paginator.per_page,
                'pages': self.page.paginator.num_pages,
                'count': self.page.paginator.count,
            },
            'results': data
        })


class PaginatedReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Base class for readonly ModelViewSets.
    """

    # Pagination
    pagination_class = ListPagination
    # filter backends
    filter_backends = (
        DjangoFilterBackend,
        RegExpSearchFilter
    )

    def list(self, request, *args, **kwargs):
        """
        """
        if self.request.GET.get('all_filtered', None):
            queryset = self.filter_queryset(self.get_queryset())
            return Response(
                queryset.values_list('pk', flat=True)
            )
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class MultiSerializerModelViewSet(viewsets.ModelViewSet):
    """
    Base class for ModelViewSets with per-request serializers.
    Custom attributes:

    * `read_serializer_class` - used for GET request
    * `write_serializer_class` - used when create/update serializers
        holds the same logic
    * `create_serializer_class` - used for POST request (creating new objects)
    * `update_serializer_class` - used for PUR/PATCH request (updating objects)
    * `delete_serializer_class` - used for DELETE request (removing objects)

    This class provide support for permissions
    """
    # Pagination
    pagination_class = ListPagination
    # filter backends
    filter_backends = (
        DjangoFilterBackend,
        RegExpSearchFilter
    )
    read_serializer_class = None
    # To be used when separate create/update serializers are not needed:
    write_serializer_class = None
    # PUT, PATCH:
    update_serializer_class = None
    # POST
    create_serializer_class = None
    # DELETE
    delete_serializer_class = None

    def get_serializer_class(self):
        """Return the class to use for the serializer."""
        method = self.request.method
        if method in ('GET', 'HEAD', 'OPTIONS'):
            serializer_class = self.read_serializer_class
        elif method == 'POST':
            serializer_class = \
                self.create_serializer_class or self.write_serializer_class
        elif method == 'DELETE':
            serializer_class = \
                self.delete_serializer_class or self.write_serializer_class
        else:  # method in ('PUT', 'PATCH')
            serializer_class = \
                self.update_serializer_class or self.write_serializer_class
        return serializer_class or self.serializer_class


class PlainTextRenderer(renderers.BaseRenderer):
    media_type = 'text/plain'
    format = 'txt'

    def render(self, data, media_type=None, renderer_context=None):
        return data
