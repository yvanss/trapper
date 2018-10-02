# -*- coding: utf-8 -*-
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.gis import admin as admin_gis
from django.conf import settings
from django.conf.urls.static import static
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from trapper.apps.accounts.views import accounts as accounts_views

admin.autodiscover()

urlpatterns = [
    # Overrides
    # Overwrite account inactive url provided by django-allauth so user
    # is redirected to homepage instead of templateless inactive user
    url(
        r'^account/inactive/$',
        RedirectView.as_view(url=reverse_lazy('trapper_index')),
        name='account_inactive'
    ),
    # Trapper homepage
    url(
        r'^$',
        accounts_views.view_index,
        name='trapper_index'
    ),
    # Media classification urls
    url(
        r'^media_classification/',
        include(
            'trapper.apps.media_classification.urls',
            namespace='media_classification'
        )
    ),
    # Research urls
    url(
        r'^research/',
        include(
            'trapper.apps.research.urls',
            namespace='research'
        )
    ),
    # Storage urls
    url(
        r'^storage/',
        include(
            'trapper.apps.storage.urls',
            namespace='storage'
        )
    ),
    # Messaging urls
    url(
        r'^messaging/',
        include(
            'trapper.apps.messaging.urls',
            namespace='messaging'
        )
    ),
    # Accounts urls
    url(
        '',
        include('django.contrib.auth.urls')
    ),
    url(
        r'^accounts/',
        include(
            'trapper.apps.accounts.urls',
            namespace='accounts'
        )
    ),
    url(
        r'^account/',
        include('allauth.urls')
    ),
    # GeoMap urls
    url(
        r'^geomap/',
        include(
            'trapper.apps.geomap.urls',
            namespace='geomap'
        )
    ),
    # Comments
    url(
        r'^comments/',
        include(
            'trapper.apps.comments.urls',
            namespace='comments'
        )
    ),
    # Sendfile urls
    url(
        r'^serve/',
        include(
            'trapper.apps.sendfile.urls',
            namespace='sendfile'
        )
    ),
    # Forum
    url(
        r'^forum/',
        include(
            'djangobb_forum.urls',
            namespace='djangobb'
        )
    ),

    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin_gis/', include(admin_gis.site.urls)),
    url(r'', include('leaflet_storage.urls')),
    # REST API Swagger docs
    url(r'^docs/api/', include('rest_framework_swagger.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = urlpatterns + [
        url(
            r'^__debug__/', 
            include(debug_toolbar.urls)
        )
    ] + static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    ) + static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )




