# -*- coding: utf-8 -*-

from django.conf.urls import url

from trapper.apps.comments import views as comments_views


urlpatterns = [

    url(
        r'^create/$',
        comments_views.view_comment_create,
        name='comment_create'
    ),
    url(
        r'^delete/(?P<pk>\d+)/$',
        comments_views.view_comment_delete,
        name='comment_delete'
    ),
]
