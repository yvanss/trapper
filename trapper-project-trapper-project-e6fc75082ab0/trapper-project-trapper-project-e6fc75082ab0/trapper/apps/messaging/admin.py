# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin

from trapper.apps.messaging.models import (
    Message, CollectionRequest
)


class MessageAdmin(admin.ModelAdmin):
    list_display = (
        'hashcode', 'date_sent', 'date_received', 'user_from', 'user_to',
        'subject', 'message_type'
    )


class CollectionRequestAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user', 'user_from', 'collection_names', 'added_at',
        'resolved_at', 'is_approved', 'message'
    )

    def collection_names(self, item):
        return ", ".join(item.collections.values_list('name', flat=True))


admin.site.register(Message, MessageAdmin)
admin.site.register(CollectionRequest, CollectionRequestAdmin)
