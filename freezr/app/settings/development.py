from __future__ import absolute_import
try:
    from .base import *  # noqa
except Exception as ex:
    print("Exception during import from base: {0}".format(ex))

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
SECRET_KEY = 'o46@o6k5p#&kw(=+-d$=5-m1!7i&weju-e_pdn&d4rz27&__@='

DEBUG = True
TEMPLATE_DEBUG = True
ALLOWED_HOSTS = []

TESTING = 'test' in sys.argv

INSTALLED_APPS = (
    'rest_framework',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djcelery',
    'django_nose',
    'freezr.api',
    'freezr.app',
    'freezr.ui',
    'freezr.core',
    'freezr.backend',
    'static_precompiler',
    )

STATICFILE_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'static_precompiler.finders.StaticPrecompilerFinder',
    )

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        # this is for testing db only, some queries to aws can last
        # multiple seconds, sqlite locks the whole db for updates, and
        # our Account.refresh uses a big hunking transaction lock
        # .. which with a real db would not be such a big problem, but
        # with sqlite will cause the default 5 second timeout to
        # .. time out
        'OPTIONS': {'timeout': 30},
    }
}

BROKER_URL = 'amqp://guest@localhost//'
CELERY_RESULT_BACKEND = 'amqp'
CELERY_TASK_RESULT_EXPIRES = 600  # 10 minutes
CELERYD_LOG_FORMAT = ('[%(asctime)s %(levelname)s/%(name)s-%(process)d] '
                      '%(message)s')
if TESTING:
    CELERY_ALWAYS_EAGER = True
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
if not TESTING:
    FORMATTER_SIMPLE_FORMAT = ('[%(asctime)s %(levelname)s/%(name)s'
                               '-%(process)d] %(message)s')
    LOGGING = {
        'version': 1,
        'formatters': {
            'simple': {
                'format': FORMATTER_SIMPLE_FORMAT,
                },
            'sql': {
                'format': FORMATTER_SIMPLE_FORMAT + " [%(duration)ss]",
                }
            },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                },
            'sql': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'sql',
                }
            },
        'loggers': {
            'freezr': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
                },
            'django.db.backends': {
                'handlers': ['sql'],
                'level': 'INFO',
                'propagate': False,
                },
            'boto': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
                },
            'celery.beat': {
                'handlers': ['console'],
                'level': 'INFO',
                'propagate': False,
                },
            }
        }

#STATIC_ROOT = os.path.join(BASE_DIR, "static")
#STATIC_ROOT = "freezr/static"

STATIC_PRECOMPILER_ROOT = "freezr/static"

STATICFILES_DIRS = (
    "freezr/static",
    '/var/www/static/',
)

FREEZR_API_ROOT = "/api"

if 'FREEZR_CLOUD_BACKEND' in os.environ:
    FREEZR_CLOUD_BACKEND = os.environ['FREEZR_CLOUD_BACKEND']

import os
if 'DONT_IMPORT_CELERY' not in os.environ:
    import freezr.backend.celery  # noqa
