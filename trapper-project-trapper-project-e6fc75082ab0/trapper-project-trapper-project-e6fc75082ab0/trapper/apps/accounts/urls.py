# -*- coding: utf-8 -*-
"""
Urls related to users management
"""
from django.conf.urls import url, include

from rest_framework.routers import DefaultRouter

from trapper.apps.accounts.views import api as api_views
from trapper.apps.accounts.views import accounts as accounts_views


router = DefaultRouter(trailing_slash=False)
router.register(
    r'users', api_views.UserViewSet, base_name='api-user'
)

urlpatterns = [

    url(r'^api/', include(router.urls)),
    url(
        r'^profile/$',
        accounts_views.view_mine_profile,
        name='mine_profile'
    ),
    url(
        r'^profile/(?P<username>[\w_\.\+\-]+)/$',
        accounts_views.view_user_profile,
        name='show_profile'
    ),
    url(
        r'^dashboard/$',
        accounts_views.view_dashbord,
        name='dashboard'
    ),
    url(
        r'^celery/cancel/$',
        accounts_views.view_celery_task_cancel,
        name='celery_task_cancel'
    ),
    url(
        r'^data-package/delete/(?P<pk>\d+)/$',
        accounts_views.view_data_package_delete,
        name='data_package_delete'
    ),
    url(
        r'^data-package/(?P<pk>\d+)/$',
        accounts_views.view_data_package_sendfile_media,
        name='data_package_sendfile_media'
    ),
]
