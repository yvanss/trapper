"""
Those settings are not required to run tests. They are defined to make little
better look & feel when you want to run coverage.

Also you can define own tablespace which with postgres will be used
to alter postgres partition (to place it i.e. in ramdisk)

To use those settings you need to install at least:

* django-coverage
* coverage

"""
from settings import *

# Uncomment this if you want to use different tablespace for testing
# (i.e. when postgres partition is located in ramdisk)
# DEFAULT_TABLESPACE = 'trapper'

INSTALLED_APPS += ('django_coverage',)

# Using this require to install coverage and django-coverage package
# It's not listed in setup.py because it's not required part of project
TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'
COVERAGE_MODULE_EXCLUDES = [
    'tests$', 'settings$', 'urls$', 'locale$', 'common.views.test',
    '__init__', 'django', 'migrations', '^(?!trapper).*$', 'static',
    'templates', 'fixtures', 'schema'
]