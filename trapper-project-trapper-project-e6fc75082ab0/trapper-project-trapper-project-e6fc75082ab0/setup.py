import os

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

requires = [
    'Django==1.9.5',
    'Jinja2==2.8',
    'Markdown==2.6.6',
    'MarkupSafe==0.23',
    'Pillow==3.1.0',
    'PyYAML==3.11',
    'Rtree==0.8.2',
    'Sphinx==1.4',
    'akismet==0.2.0',
    'amqp==1.4.9',
    'anyjson==0.3.3',
    'astroid==1.4.5',
    'billiard==3.3.0.23',
    'celery==3.1.23',
    'django-allauth==0.25.2',
    'django-braces==1.8.1',
    'django-bulk-update==1.1.10',
    'django-celery==3.1.17',
    'django-crispy-forms==1.6.0',
    'django-debug-toolbar==1.4',
    'django-extensions==1.6.1',
    'django-extra-views==0.7.1',
    'django-filter==0.13.0',
    'django-formtools==1.0',
    'django-grappelli==2.8.1',
    'django-hstore==1.4.2',
    'django-import-export==0.4.5',
    'django-leaflet-storage==0.8.0b0',
    'django-mptt==0.8.3',
    'django-recaptcha==1.0.5',
    'django-rest-swagger==0.3.5',
    'django-taggit==0.19.1',
    'django-timezone-field==1.3',
    'django-tinymce==2.3.0',
    'djangorestframework==3.3.3',
    'djangorestframework-gis==0.10.1',
    'docopt==0.6.2',
    'docutils==0.12',
    'funcy==1.7.1',
    'gunicorn==19.4.5',
    'ipdb==0.9.0',
    'kombu==3.0.35',
    'logilab-common==1.2.0',
    'lxml==3.6.0',
    'mock==2.0.0',
    'numpy==1.11.0',
    'pandas==0.18.0',
    'psycopg2==2.6.1',
    'pygeocoder==1.2.5',
    'pykwalify==1.5.1',
    'python-dateutil==2.5.2',
    'python-memcached==1.57',
    'pytz==2016.3',
    'rest-pandas==0.4.0',
    'simplejson==3.8.2',
    'six==1.10.0',
    'sqlparse==0.1.19',
    'supervisor==3.2.3',
    'tablib==0.11.2',
    'Whoosh==2.7.0',
]

setup(
    name='trapper',
    version='1.0.1',
    description='Trapper',
    author='trapper-project.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
)
