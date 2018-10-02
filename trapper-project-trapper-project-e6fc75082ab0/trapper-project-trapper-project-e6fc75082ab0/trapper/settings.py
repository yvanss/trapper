# Django settings for trapper project.

import os
from django.contrib.messages import constants as messages

DEBUG = True

DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK" : 'trapper.settings.show_toolbar',
}

# override it in your settings_local.py
SHOW_DEBUG_TOOLBAR_USERS = (
    # 'username1', 'username2'
)

def show_toolbar(request):
    return request.user and request.user.username in SHOW_DEBUG_TOOLBAR_USERS

ADMINS = (
    # ('Your Name', 'your_email@example.com')
)
MANAGERS = ADMINS

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

# Uncomment this line if your postgis is 2.1 or newer
# (input the correct version in that case)
POSTGIS_VERSION = (2, 1, 3)

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'trapper_db',
        'USER': 'trapper',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '',
    }
}


EMAIL_NOTIFICATIONS = True
EMAIL_NOTIFICATIONS_RESEARCH_PROJECT = True
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# EMAIL_USE_TLS = True
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_HOST_USER = 'xxx@gmail.com'
# EMAIL_HOST_PASSWORD = ''
# EMAIL_PORT = 587

DOMAIN_NAME = 'localhost'

DATE_INPUT_FORMATS = ('%d-%m-%Y', '%Y-%m-%d', '%d.%m.%Y', '%Y.%m.%d')
DATETIME_INPUT_FORMATS = (
    '%d-%m-%Y %H:%M:%S',
    '%Y-%m-%d %H:%M:%S',
    '%d.%m.%Y %H:%M:%S',
    '%Y.%m.%d %H:%M:%S'
)
TIME_INPUT_FORMATS = ('%H:%M:%S', '%H:%M')

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ['*']

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Warsaw'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
EXTERNAL_MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'external_media')

# Configure upload limits
UPLOAD_LIMIT = True
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
MAX_UPLOAD_COLLECTION_SIZE = 500 * 1024 * 1024

# max size of a raw data package
DATA_PACKAGE_MAX_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_FILE_TYPES = (
        'aac', 'ace', 'ai', 'aiff', 'avi', 'bmp', 'fla', 'flv', 
        'jpg', 'jpeg', 'mov', 'mp3', 'mp4', 'mpc', 'mkv',
        'mpg', 'mpeg', 'ogg', 'odg', 'ogv', 'pdf', 'png', 
        'swf', 'tif', 'tiff', 'wav', 'webm', 'wma',
        'wmv', 'zip', 'csv', 'gpx'
)

CELERY_DATA_ROOT = os.path.join(PROJECT_ROOT, 'celery_data')
CELERY_IMPORTS = [
    'celery.task.http'
]
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack', 'yaml']
# Setting used to determine if task should be run as celery task or regular one
CELERY_ENABLED = True
# Min image size for resource to be processed by celery.
# If size is lower - image will be processed without celery
CELERY_MIN_IMAGE_SIZE = 10 * 1024 * 1024

BROKER_URL = 'amqp://guest:guest@localhost:5672//'
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
CELERY_RESULT_BACKEND = 'djcelery.backends.database.DatabaseBackend'
CELERY_TRACK_STARTED = True
CELERY_SEND_EVENTS = True

BROKER_POOL_LIMIT = 2
CELERYD_CONCURRENCY = 1
CELERY_DISABLE_RATE_LIMITS = True
CELERYD_MAX_TASKS_PER_CHILD = 20
CELERYD_SOFT_TASK_TIME_LIMIT = 5 * 60
CELERYD_TASK_TIME_LIMIT = 6 * 60

import djcelery
djcelery.setup_loader()

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'
EXTERNAL_MEDIA_URL = '/external_media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = os.path.join(PROJECT_ROOT, '..', 'static').replace('\\', '/')
# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

LOGIN_URL = '/account/login/'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'allauth.account.auth_backends.AuthenticationBackend',
)

AUTH_USER_MODEL = 'accounts.User'
AUTH_PROFILE_MODULE = 'accounts.UserProfile'

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

# Make this unique, and don't share it with anybody.
# This should be kept in your settings_local.py
SECRET_KEY = 'YOUR_SECRET_KEY_HERE'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            # 'theme_templates' directory is not commited to git; this is a simple 
            # way to customize your Trapper instance
            os.path.join(PROJECT_ROOT, 'theme_templates').replace('\\', '/'),
            os.path.join(PROJECT_ROOT, 'templates').replace('\\', '/'),
        ],
        'APP_DIRS': False,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.core.context_processors.static',
                'django.core.context_processors.media',
                'django.core.context_processors.request',
                'djangobb_forum.context_processors.forum_settings',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'builtins': [
                'trapper.apps.accounts.templatetags.accounts_tags'
            ],
        },
    },
]

MIDDLEWARE_CLASSES = [
    # ThreadLocals middleware should be first since it stores data in
    # local thread and since it's first - data cleared in process_response and
    # process_exception will be available for all other middlewares
    'trapper.middleware.ThreadLocals',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'trapper.middleware.TimezoneMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'trapper.apps.sendfile.middleware.SendFileDevServerMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

ROOT_URLCONF = 'trapper.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'trapper.wsgi.application'

DEFAULT_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'formtools',
    'grappelli',
    'django.contrib.admin',
    'leaflet_storage',
    'django_extensions',
    'tinymce',
    'crispy_forms',
    'django_hstore',
    'rest_framework',
    'rest_framework_gis',
    'rest_framework_swagger',
    'allauth',
    'allauth.account',
    'mptt',
    'taggit',
    'djcelery',
    'import_export',
    'timezone_field',
    'debug_toolbar',
    'captcha',
    'haystack',
    'djangobb_forum',
]

LOCAL_APPS = [
    'trapper.apps.accounts',
    'trapper.apps.comments',
    'trapper.apps.dashboard',
    'trapper.apps.variables',
    'trapper.apps.extra_tables',
    'trapper.apps.storage',
    'trapper.apps.research',
    'trapper.apps.geomap',
    'trapper.apps.media_classification',
    'trapper.apps.messaging',
    'trapper.apps.common',
    'trapper.apps.sendfile',
]

INSTALLED_APPS = DEFAULT_APPS + LOCAL_APPS


MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.DEBUG: 'info',
}

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

LOG_DIR = os.path.join(PROJECT_ROOT, '..', 'logs')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': (
                "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s"
            ),
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'logfile': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, "logfile"),
            'maxBytes': 50000,
            'backupCount': 2,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'logfile'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

# CRISPY FORMS
CRISPY_TEMPLATE_PACK = 'bootstrap3'
CRISPY_FAIL_SILENTLY = not DEBUG
CRISPY_CLASS_CONVERTERS = {
    # 'select': "select2-default",
    'selectmultiple': "select2-default",
    'textarea': 'textarea-wysiswyg',
    'datetimeinput': 'datetimepicker-control',
    'dateinput': 'datepicker-control',
    'tagwidget': 'select2-tags',
}

# Time (in seconds) how often request for resource/collection can be sent
REQUEST_FLOOD_DELAY = 86400

# Django REST Framework settings:
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
    ),
    'PAGINATE_BY': None,
    'PAGINATE_BY_PARAM': 'page_size',
    'MAX_PAGINATE_BY': 999,
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

SWAGGER_SETTINGS = {
    # List URL namespaces to ignore
    "exclude_namespaces": [],
    # Specify your API's version
    "api_version": '1.0',
    # Specify the path to your API not a root level
    "api_path": "/",
    # Specify which methods to enable in Swagger UI
    "enabled_methods": [
        'get',
        'post',
        'put',
        'patch',
        'delete'
    ],
    # An API key
    "api_key": '',
    # Set to True to enforce user authentication,
    "is_authenticated": True,
    # Set to True to enforce admin only access
    "is_superuser": False,
    # If user has no permisssion, raise 403 error
    "permission_denied_handler": None,
}

USE_RECAPTCHA = False
# update recaptcha keys in settings_local.py
RECAPTCHA_PUBLIC_KEY = ''
RECAPTCHA_PRIVATE_KEY = ''
RECAPTCHA_USE_SSL = True
NOCAPTCHA = True

# Django allauth settings
ACCOUNT_ADAPTER = 'trapper.apps.accounts.adapters.TrapperAdapter'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_SESSION_REMEMBER = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_ON_GET = True


# Dashboard settings
MESSAGES_COUNT = 5

# Variables settings
VARIABLES_DEBUG = DEBUG

# Comments settings
COMMENTS_REDIRECT_URL = '/'

DEFAULT_THUMBNAIL_SIZE = (136, 136)
DEFAULT_PREVIEW_SIZE = (860,860)
VIDEO_THUMBNAIL_ENABLED = True

CACHE_UNDEFINED = '_UNDEFINED_'
CACHE_TIMEOUT = 43200  # 30 days

DASHBOARD_TASKS = 10

# Exclude the number-based attributes (e.g. number of animals)
# from the classification list filters
EXCLUDE_CLASSIFICATION_NUMBERS = True

REVERSE_GEOCODING = False

# Base place for media that should be served through x-sendfile
SENDFILE_ROOT = MEDIA_URL

# Default directory within SENDFILE_ROOT for files served through x-sendfile
SENDFILE_MEDIA_PREFIX = 'protected/'

# Used by middleware to fake sendfile on development instances
# DO NOT USE IT ON PRODUCTION
SENDFILE_DEV_SERVER_ENABLED = False

# Header that will be added to response. Differes between web servers.
# This one is for nginx
SENDFILE_HEADER = 'X-Accel-Redirect'

RESOURCE_FORBIDDEN_THUMBNAIL = 'trapper_storage/img/thumb_forbidden.jpg'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

# FORUM Settings
DJANGOBB_FORUM_BASE_TITLE = 'Trapper'
DJANGOBB_FORUM_META_DESCRIPTION = ''
DJANGOBB_FORUM_META_KEYWORDS = ''
DJANGOBB_HEADER = 'Trapper Forum'
DJANGOBB_TAGLINE = 'discussion forum'

# Haystack settings
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(PROJECT_ROOT, 'djangobb_index'),
        'INCLUDE_SPELLING': True,
    },
}
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

# Private settings should be held down in settings_local module, which
# won't be commited into repository

local_settings = os.path.join(PROJECT_ROOT, 'settings_local.py')
if os.path.exists(local_settings):
    from settings_local import *

# settings that should be verified after the import of local settings
if USE_RECAPTCHA:
    ACCOUNT_SIGNUP_FORM_CLASS = 'trapper.apps.accounts.forms.TrapperSignupForm'

# settings for management command delete_orphaned
ORPHANED_APPS_MEDIABASE_DIRS = {
    'storage': {
        'root': os.path.join(MEDIA_ROOT, 'protected/storage'),
        'exclude': ('.gitignore',)
    },
}
