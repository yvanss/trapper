from django.conf.urls import url
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from trapper.apps.messaging import views as messaging_views


urlpatterns = [
    url(
        r'^$',
        RedirectView.as_view(url=reverse_lazy('messaging:message_inbox')),
        name='index'
    ),
    url(
        r'message/detail/(?P<hashcode>\w+)/$',
        messaging_views.view_message_detail,
        name='message_detail'
    ),
    url(
        r'message/inbox/$',
        messaging_views.view_message_inbox,
        name='message_inbox'
    ),
    url(
        r'message/outbox/$',
        messaging_views.view_message_outbox,
        name='message_outbox'
    ),
    url(
        r'message/create/$',
        messaging_views.view_message_create,
        name='message_create'
    ),
    url(
        r'collection-request/list/$',
        messaging_views.view_collection_request_list,
        name='collection_request_list'
    ),
    url(
        r'collection-request/resolve/(?P<pk>\d+)/$',
        messaging_views.view_collection_request_resolve,
        name='collection_request_resolve'
    ),
    url(
        r'collection-request/revoke/(?P<pk>\d+)/$',
        messaging_views.view_collection_request_revoke,
        name='collection_request_revoke'
    ),
]
