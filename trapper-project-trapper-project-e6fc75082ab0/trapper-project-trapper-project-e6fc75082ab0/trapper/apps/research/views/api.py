# -*- coding: utf-8 -*-
"""Views used by DRF to display json data used by research application"""

from trapper.apps.common.views_api import PaginatedReadOnlyModelViewSet
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectCollection
)
from trapper.apps.research import serializers as research_serializers
from trapper.apps.research.filters import (
    ResearchProjectFilter, ResearchProjectCollectionFilter
)
from trapper.apps.research.taxonomy import ResearchProjectRoleType


class ResearchProjectViewSet(PaginatedReadOnlyModelViewSet):
    """Return list of research projects.
    List of projects is limited only to those which are accessible
    for current user (if provided)
    """
    serializer_class = research_serializers.ResearchProjectSerializer
    filter_class = ResearchProjectFilter
    search_fields = ['name', 'acronym', 'abstract', 'owner__username']
    select_related = [
        'owner',
    ]

    def get_queryset(self):
        """Limit projects depend on user login status

        * if GET contains `only-with-roles` then projects are limited to only
            those in which user has at least single role
        * if GET contains `only-updateable` then projects are limited to only
            those which user can update
        """
        base_querset = ResearchProject.objects.all()
        params = {
            'base_queryset': base_querset
        }

        user = self.request.user
        is_authenticated = user.is_authenticated()
        if is_authenticated and 'only-with-roles' in self.request.GET:
            params['user'] = user

        if is_authenticated and 'only-updateable' in self.request.GET:
            params['user'] = user
            params['role_levels'] = ResearchProjectRoleType.EDIT

        if 'no-pagination' in self.request.GET:
            self.pagination_class = None

        queryset = ResearchProject.objects.get_accessible(**params)
        return queryset.distinct().select_related(
            *self.select_related
        ).prefetch_related(
            'keywords', 'project_roles__user'
        )


class ResearchProjectCollectionViewSet(PaginatedReadOnlyModelViewSet):
    """Return list of research project collections.
    List of project collections is limited only to those which are accessible
    for current user (if provided)
    """
    serializer_class = research_serializers.ResearchProjectCollectionSerializer
    filter_class = ResearchProjectCollectionFilter
    search_fields = ['collection__name', 'collection__owner__username']
    select_related = [
        'collection', 'collection__owner', 'project'
    ]

    def get_queryset(self):
        """Limit project collections depend on user login status"""
        base_queryset = ResearchProjectCollection.objects.all()
        return ResearchProjectCollection.objects.get_accessible(
            base_queryset=base_queryset
        ).distinct().select_related(
            *self.select_related
        )
