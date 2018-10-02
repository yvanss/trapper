# -*- coding: utf-8 -*-

from django.conf.urls import url

from trapper.apps.sendfile import views as sendfile_views


urlpatterns = [
    url(
        r'^direct/$',
        sendfile_views.view_direct_serve_file,
        name='sendfile_direct_serve'
    ),
]

