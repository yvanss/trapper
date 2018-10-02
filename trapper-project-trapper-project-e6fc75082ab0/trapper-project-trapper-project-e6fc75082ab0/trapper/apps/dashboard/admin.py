# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin

from models import DashboardButton


class DashboardButtonAdmin(admin.ModelAdmin):
    list_display = ("name", "href", "url", "css_class")


admin.site.register(DashboardButton, DashboardButtonAdmin)
