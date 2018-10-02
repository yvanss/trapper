# -*- coding: utf-8 -*-
"""
Simple admin interface to control changes in models.
"""

from django.contrib import admin
from mptt.admin import MPTTModelAdmin

from trapper.apps.comments.models import UserComment

admin.site.register(UserComment, MPTTModelAdmin)
