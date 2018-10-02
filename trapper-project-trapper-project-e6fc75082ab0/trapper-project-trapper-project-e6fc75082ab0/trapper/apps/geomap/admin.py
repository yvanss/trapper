# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib.gis import admin
from trapper.apps.geomap.models import Location, Deployment
from trapper.apps.geomap.widgets import TrapperOSMGeoAdmin


class LocationAdmin(TrapperOSMGeoAdmin):
    list_display = (
        'location_id', 'name', 'city', 'county', 'state', 'country',
        'is_public'
    )

class DeploymentAdmin(admin.ModelAdmin):
    list_display = (
        'deployment_id', 'deployment_code', 'location',
        'research_project', 'start_date', 'end_date'
    )

    def get_queryset(self, request):
        return super(
            DeploymentAdmin, self
        ).get_queryset(
            request
        ).prefetch_related(
            'location', 'research_project'
        )


admin.site.register(Location, LocationAdmin)
admin.site.register(Deployment, DeploymentAdmin)
