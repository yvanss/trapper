# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin

from trapper.apps.media_classification.models import (
    Classificator, Classification, ClassificationDynamicAttrs,
    UserClassification,
    ClassificationProject,
    ClassificationProjectRole, ClassificationProjectCollection, Sequence,
    ClassificatorHistory, UserClassificationDynamicAttrs
)


class ClassificationAdmin(admin.ModelAdmin):
    pass


class ClassificationUserAdmin(admin.ModelAdmin):
    pass


class ProjectRoleInline(admin.TabularInline):
    model = ClassificationProjectRole
    extra = 0


class ProjectCollectionInline(admin.TabularInline):
    model = ClassificationProjectCollection
    extra = 0


class ClassificationProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectRoleInline, ProjectCollectionInline]
    filter_horizontal = ('collections',)
    list_display = (
        'name', 'research_project', 'classificator', 'owner',
        'date_created', 'disabled_at', 'disabled_by'
    )


class ClassificatorHistoryAdmin(admin.ModelAdmin):
    list_display = ('classification_project', 'classificator', 'change_date')


class UserClassificationDynamicAttrsAdmin(admin.ModelAdmin):
    list_display = ('pk', 'attrs')


class ClassificationDynamicAttrsAdmin(admin.ModelAdmin):
    list_display = ('pk', 'attrs')


class ClassificatorAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'name', 'copy_of', 'created_date', 'updated_date',
        'disabled_at', 'disabled_by', 'template'
    )


class ClassificationProjectCollectionAdmin(admin.ModelAdmin):
    list_display = (
        'pk', 'project', 'collection', 'is_active',
        'enable_sequencing_experts', 'enable_crowdsourcing'
    )


admin.site.register(Classificator, ClassificatorAdmin)
admin.site.register(
    ClassificationProjectCollection, ClassificationProjectCollectionAdmin
)
admin.site.register(Classification, ClassificationAdmin)
admin.site.register(UserClassification, ClassificationUserAdmin)
admin.site.register(ClassificationProjectRole)
admin.site.register(Sequence)
admin.site.register(ClassificationProject, ClassificationProjectAdmin)
admin.site.register(ClassificatorHistory, ClassificatorHistoryAdmin)
admin.site.register(
    UserClassificationDynamicAttrs,
    UserClassificationDynamicAttrsAdmin
)
admin.site.register(
    ClassificationDynamicAttrs,
    ClassificationDynamicAttrsAdmin
)
