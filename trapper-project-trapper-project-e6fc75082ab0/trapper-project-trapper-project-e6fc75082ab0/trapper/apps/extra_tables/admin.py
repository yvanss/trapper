# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin
from django.utils.safestring import mark_safe

from trapper.apps.extra_tables.models import Species

from import_export import resources

from import_export.admin import ImportExportModelAdmin


class SpeciesResource(resources.ModelResource):

    class Meta:
        model = Species


class SpeciesAdmin(ImportExportModelAdmin):
    list_display = [
        'english_name', 'latin_name', 'family', 'genus', 'eol_link'
    ]
    list_filter = ['family', 'genus']
    search_fields = ['english_name', 'latin_name', 'family', 'genus']

    def eol_link(self, instance):
        return mark_safe((
            u'<a href="http://eol.org/search?q=%s&search=Go" '
            u'target="_blank">Go</a>'
        ) % instance.latin_name)
    eol_link.short_description = 'EOL link'

    resource_class = SpeciesResource

    pass


admin.site.register(Species, SpeciesAdmin)
