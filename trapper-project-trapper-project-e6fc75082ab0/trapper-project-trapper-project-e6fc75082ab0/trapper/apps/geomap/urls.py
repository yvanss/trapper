# -*- coding: utf-8 -*-

from django.conf.urls import url, include
from django.core.urlresolvers import reverse_lazy
from django.views.generic import TemplateView, RedirectView
from django.views.decorators.cache import never_cache

from leaflet_storage.utils import decorated_patterns
from leaflet_storage.decorators import map_permissions_check
from leaflet_storage import views as ls_views

from rest_framework.routers import DefaultRouter

from trapper.apps.geomap.views import api as api_views
from trapper.apps.geomap.views import map as map_views
from trapper.apps.geomap.views import location as location_views
from trapper.apps.geomap.views import deployment as deployment_views


router = DefaultRouter(trailing_slash=False)
router.register(
    r'locations',
    api_views.LocationViewSet,
    base_name='api-location'
)

router.register(
    r'deployments',
    api_views.DeploymentViewSet,
    base_name='api-deployment'
)

router.register(
    r'maps',
    api_views.MapViewSet,
    base_name='api-map'
)

urlpatterns = [
    url(
        r'^api/locations/export/$',
        api_views.LocationTableView.as_view(),
        name='api-location-export'
    ),
    url(
        r'^api/deployments/export/$',
        api_views.DeploymentTableView.as_view(),
        name='api-deployment-export'
    ),
    url(
        r'^api/locations/geojson/$',
        api_views.LocationGeoViewSet.as_view(),
        name='api-location-geojson'
    ),
    url(r'^api/', include(router.urls))
]

urlpatterns += [

    url(
        r'^location/bulk-update/$',
        location_views.view_location_bulk_update,
        name='location_bulk_update'
    ),
    url(
        r'^location/create/$',
        RedirectView.as_view(url=u'/geomap/map/?action=create'),
        name='location_create'
        ),
    url(
        r'^location/(?P<pk>\d+)/delete/$',
        location_views.view_location_delete,
        name='location_delete'
    ),
    url(
        r'^location/delete/$',
        location_views.view_location_delete,
        name='location_delete_multiple'
    ),
    url(r'^location/list/$',
        location_views.view_location_list,
        name='location_list'
    ),
    url(
        r'^location/import/$',
        location_views.view_location_import,
        name='location_import'
    ),
    url(
        r'^location/filterform/$',
        location_views.view_location_filter_form,
        name="locations_filterform"
    ),
    url(
        r'^location/createform/$',
        location_views.view_location_create_form,
        name="locations_createform"
    ),
    url(
        r'^location/(?P<pk>\d+)/editform/$',
        location_views.view_location_edit_filter_form,
        name="locations_editform"
    ),
    url(
        r'^location/collections/$',
        location_views.view_location_collections,
        name="location_collections"
    ),
]

urlpatterns += [

    url(
        r'^map/permissions/update/(?P<map_id>[\d]+)/$',
        map_views.view_update_map_permissions,
        name="map_permissions"
    ),
    url(
        r'^map/(?P<slug>[-_\w]+)_(?P<pk>\d+)$',
        map_views.view_map, 
        name='map'
    ),
    url(
        r'^map/list/$', 
        map_views.view_map_list, 
        name="map_list"),
    url(
        r'^map/(?P<pk>\d+)/delete/$',
        map_views.view_map_delete,
        name='map_delete'
    ),
    url(
        r'^map/delete/$',
        map_views.view_map_delete,
        name='map_delete_multiple'
    ),
    url(
        r'^map/$', 
        map_views.view_new_map, 
        name='map_view'
    ),
    url(
        r'permissions/update/(?P<map_id>\d+)/$',
        map_views.view_update_map_permissions,
        name='map_permissions'
    ),
    url(
        r'^map/create/$', 
        map_views.view_map_create, 
        name='map_create'
    ),
]

urlpatterns += [
    url(r'^map/(?P<map_id>[\d]+)/update/settings/$',
        ls_views.MapUpdate.as_view(), name='map_update'),
    url(r'^map/(?P<map_id>[\d]+)/update/permissions/$',
        ls_views.UpdateMapPermissions.as_view(),
        name='map_update_permissions'),
    url(r'^map/(?P<map_id>[\d]+)/update/delete/$',
        ls_views.MapDelete.as_view(), name='map_delete'),
    url(r'^map/(?P<map_id>[\d]+)/update/clone/$',
        ls_views.MapClone.as_view(), name='map_clone'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/create/$',
        ls_views.DataLayerCreate.as_view(), name='datalayer_create'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/update/(?P<pk>\d+)/$',
        ls_views.DataLayerUpdate.as_view(), name='datalayer_update'),
    url(r'^map/(?P<map_id>[\d]+)/datalayer/delete/(?P<pk>\d+)/$',
        ls_views.DataLayerDelete.as_view(), name='datalayer_delete'),
]

urlpatterns += [

    # Deployments
    url(
        r'^deployment/$',
        RedirectView.as_view(url=reverse_lazy('geomap:deployment_list')),
        name='deployment_index'
    ),
    url(
        r'^deployment/list/$',
        deployment_views.view_deployment_list,
        name='deployment_list'
    ),
    url(
        r'^deployment/detail/(?P<pk>\d+)/$',
        deployment_views.view_deployment_detail,
        name='deployment_detail'
    ),
    url(
        r'^deployment/delete/(?P<pk>\d+)/$',
        deployment_views.view_deployment_delete,
        name='deployment_delete'
    ),
    url(
        r'^deployment/delete/$',
        deployment_views.view_deployment_delete,
        name='deployment_delete_multiple'
    ),
    url(
        r'^deployment/create/$',
        deployment_views.view_deployment_create,
        name='deployment_create'
    ),
    url(
        r'^deployment/update/(?P<pk>\d+)/$',
        deployment_views.view_deployment_update,
        name='deployment_update'
    ),
    url(
        r'^deployment/bulk-update/$',
        deployment_views.view_deployment_bulk_update,
        name='deployment_bulk_update'
    ),
    url(
        r'^deployment/bulk-create/$',
        deployment_views.view_deployment_bulk_create,
        name='deployment_bulk_create'
    ),
    url(
        r'deployment/import/$',
        deployment_views.view_deployment_import,
        name='deployment_import'
    ),
]
