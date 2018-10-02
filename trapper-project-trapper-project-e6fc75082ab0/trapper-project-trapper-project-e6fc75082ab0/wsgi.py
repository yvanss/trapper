# -*- coding: utf-8 -*-

import os
import sys

sys.path = sys.path[::-1]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trapper.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
