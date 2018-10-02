# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin
from trapper.apps.storage.models import (
    Resource, Collection, CollectionMember
)


class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', )


class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'owner', 'status', 'prefixed_name', 'deployment',
        'inherit_prefix', 'custom_prefix',
    )

    def get_queryset(self, request):
        return super(
            ResourceAdmin, self
        ).get_queryset(
            request
        ).prefetch_related(
            'owner', 'deployment'
        )

    def deployment_id(self, item):
        if item.deployment:
            return item.deployment_id
        else:
            return u''


class CollectionMemberAdmin(admin.ModelAdmin):
    search_fields = (
        'collection__name',
    )
    list_display = (
        'collection', 'user', 'get_level_display', 'date_created'
    )
    list_filter = ('level', 'user')


admin.site.register(Resource, ResourceAdmin)
admin.site.register(Collection, CollectionAdmin)
admin.site.register(CollectionMember, CollectionMemberAdmin)
