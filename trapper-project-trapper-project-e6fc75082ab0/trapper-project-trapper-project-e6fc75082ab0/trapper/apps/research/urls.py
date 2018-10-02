# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

from trapper.apps.research.views import api as api_views
from trapper.apps.research.views import research as research_views


router = DefaultRouter(trailing_slash=False)
router.register(
    r'research-projects',
    api_views.ResearchProjectViewSet,
    base_name='api-research-project'
)
router.register(
    r'research-project-collections',
    api_views.ResearchProjectCollectionViewSet,
    base_name='api-research-project-collection'
)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(
        r'^$',
        RedirectView.as_view(url=reverse_lazy('research:project_list')),
        name='project_index'
    ),
]

urlpatterns += [

    url(
        r'project/list/$',
        research_views.view_research_project_list,
        name='project_list'
    ),
    url(
        r'project/detail/(?P<pk>\d+)/$',
        research_views.view_research_project_detail,
        name='project_detail'
    ),
    url(
        r'project/create/$',
        research_views.view_research_project_create,
        name='project_create'
    ),
    url(
        r'project/update/(?P<pk>\d+)/$',
        research_views.view_research_project_update,
        name='project_update'
    ),
    url(
        r'project/delete/(?P<pk>\d+)/$',
        research_views.view_research_project_delete,
        name='project_delete'
    ),
    url(
        r'^project/delete/$',
        research_views.view_research_project_delete,
        name='project_delete_multiple'
    ),
    url(
        r'project/collection/add/$',
        research_views.view_research_project_collection_add,
        name='project_collection_add'
    ),
    url(
        r'^project/collection/delete/$',
        research_views.view_research_project_collection_delete,
        name='project_collection_delete_multiple'
    ),
    url(
        r'^project/collection/delete/(?P<pk>\d+)/$',
        research_views.view_research_project_collection_delete,
        name='project_collection_delete'
    ),
]
