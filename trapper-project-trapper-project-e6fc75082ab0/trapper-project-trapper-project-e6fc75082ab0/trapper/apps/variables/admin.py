# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin
from .models import Variable


class VariableAdmin(admin.ModelAdmin):
    list_display = ['namespace', 'name', 'value']

admin.site.register(Variable, VariableAdmin)
