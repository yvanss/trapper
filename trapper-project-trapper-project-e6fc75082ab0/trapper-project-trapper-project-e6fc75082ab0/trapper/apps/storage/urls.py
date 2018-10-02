# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from rest_framework.routers import DefaultRouter

from trapper.apps.storage.views import api as api_views
from trapper.apps.storage.views import resource as resource_views
from trapper.apps.storage.views import collection as collection_views


router = DefaultRouter(trailing_slash=False)
router.register(
    r'resources', api_views.ResourceViewSet, base_name='api-resource'
)
router.register(
    r'resources_map', api_views.ResourceMapViewSet, base_name='api-resource-map'
)
router.register(
    r'collections', api_views.CollectionViewSet, base_name='api-collection'
)
router.register(
    r'collections_ondemand', api_views.CollectionOnDemandViewSet, base_name='api-collection-ondemand'
)
router.register(
    r'collections_map', api_views.CollectionMapViewSet, base_name='api-collection-map'
)
router.register(
    r'collections_append', api_views.CollectionAppendViewSet, base_name='api-collection-append'
)

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(
        r'^$',
        RedirectView.as_view(url=reverse_lazy('storage:resource_list')),
        name='storage_index'
    ),
]

urlpatterns += [

    # Resources
    url(
        r'^resource/$',
        RedirectView.as_view(url=reverse_lazy('storage:resource_list')),
        name='resource_index'
    ),
    url(
        r'^resource/list/$',
        resource_views.view_resource_list,
        name='resource_list'
    ),
    url(
        r'^resource/detail/(?P<pk>\d+)/$',
        resource_views.view_resource_detail,
        name='resource_detail'
    ),
    url(
        r'^resource/delete/(?P<pk>\d+)/$',
        resource_views.view_resource_delete,
        name='resource_delete'
    ),
    url(
        r'^resource/delete/$',
        resource_views.view_resource_delete,
        name='resource_delete_multiple'
    ),
    url(
        r'^resource/define-prefix/$',
        resource_views.view_resource_define_prefix,
        name='resource_define_prefix'
    ),
    url(
        r'^resource/create/$',
        resource_views.view_resource_create,
        name='resource_create'
    ),
    url(
        r'^resource/update/(?P<pk>\d+)/$',
        resource_views.view_resource_update,
        name='resource_update'
    ),
    url(
        r'^resource/bulk-update/$',
        resource_views.view_resource_bulk_update,
        name='resource_bulk_update'
    ),
    url(
        r'resource/rate_resource/',
        resource_views.view_rate_resource,
        name='rate_resource'
    ),
    url(
        r'^resource/data-package/',
        resource_views.view_resource_data_package,
        name='resource_data_package'
    ),
    url(
        r'^resource/media/(?P<pk>\d+)/(?P<field>(p|t|e)?(file))/$',
        resource_views.view_resource_sendfile_media,
        name='resource_sendfile_media'
    ),

    # Collections
    url(
        r'^collection/$',
        RedirectView.as_view(url=reverse_lazy('storage:collection_list')),
        name='collection_index'
    ),
    url(
        r'^collection/list/$',
        collection_views.view_collection_list,
        name='collection_list'
    ),
    url(
        r'^collection/list/ondemand/$',
        collection_views.view_collection_ondemand_list,
        name='collection_ondemand_list'
    ),
    url(
        r'^collection/detail/(?P<pk>\d+)/$',
        collection_views.view_collection_detail,
        name='collection_detail'
    ),
    url(
        r'^collection/append/$',
        collection_views.view_collection_resource_append,
        name='collection_append'
    ),
    url(
        r'^collection/delete/$',
        collection_views.view_collection_delete,
        name='collection_delete_multiple'
    ),
    url(
        r'^collection/delete/(?P<pk>\d+)/$',
        collection_views.view_collection_delete,
        name='collection_delete'
    ),
    url(
        r'^collection/upload/(?P<pk>\d+)/$',
        collection_views.view_collection_upload,
        name='collection_upload'
    ),
    url(
        r'^collection/update/(?P<pk>\d+)/$',
        collection_views.view_collection_update,
        name='collection_update'
    ),
    url(
        r'^collection/resource-delete/(?P<pk>\d+)/$',
        collection_views.view_collection_resource_delete,
        name='collection_resource_delete'
    ),
    url(
        r'^collection/create/$',
        collection_views.view_collection_create,
        name='collection_create'
    ),
    url(
        r'^collection/upload/$',
        collection_views.view_collection_upload,
        name='collection_upload'
    ),
    url(
        r'^collection/delete/(?P<pk>\d+)$',
        collection_views.view_collection_delete,
        name='collection_delete'
    ),
    url(
        r'^collection/request/(?P<pk>\d+)/$',
        collection_views.view_collection_request,
        name='collection_request'
    ),
    url(
        r'^collection/bulk-update/$',
        collection_views.view_collection_bulk_update,
        name='collection_bulk_update'
    ),
    url(
        r'^collection/resource-delete-orphaned/(?P<pk>\d+)/$',
        collection_views.view_collection_resource_delete_orphaned,
        name='collection_resource_delete_orphaned'
    ),
]
