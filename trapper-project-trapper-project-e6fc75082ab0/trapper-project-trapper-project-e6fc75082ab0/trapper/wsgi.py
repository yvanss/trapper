# -*- coding: utf-8 -*-

import os
import sys
import site

site.addsitedir("/root/apps/trapper/lib/python2.7/site-packages")

sys.path.append("/root/apps/trapper/src")
sys.path.append("/root/apps/trapper/src/trapper")

sys.path = sys.path[::-1]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trapper.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
