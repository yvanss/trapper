# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.

Admin is used to approve or reject research projects created
by users
"""

from django.contrib import admin
from trapper.apps.research.models import (
    ResearchProject, ResearchProjectRole, ResearchProjectCollection
)


class ProjectRoleInline(admin.TabularInline):
    model = ResearchProjectRole
    extra = 0


class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectRoleInline, ]
    filter_horizontal = ('collections',)
    exclude = ('keywords',)

admin.site.register(ResearchProjectRole)
admin.site.register(ResearchProjectCollection)
admin.site.register(ResearchProject, ProjectAdmin)
