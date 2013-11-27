"""
Django settings for freezr project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import datetime
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'o46@o6k5p#&kw(=+-d$=5-m1!7i&weju-e_pdn&d4rz27&__@='

# SECURITY WARNING: don't run with debug turned on in production!
if False:
    DEBUG = True
    TEMPLATE_DEBUG = True
    ALLOWED_HOSTS = []
else:
    DEBUG = False
    TEMPLATE_DEBUG = False
    ALLOWED_HOSTS = ['*']

TESTING = 'test' in sys.argv

if TESTING:
    print("========================================================================")
    print("TESTING enabled\n")

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'freezr',
    'djcelery',
    'django_nose',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'freezr.urls'

WSGI_APPLICATION = 'freezr.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

# Celery configuration
#CELERY_RESULT_BACKEND='djcelery.backends.database:DatabaseBackend'
#CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

BROKER_URL = 'amqp://guest@localhost//'
CELERY_TIMEZONE = 'UTC'
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_IMPORTS = ('freezr.celery', 'freezr.celery.tasks')
CELERYD_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s-%(process)d] %(message)s'

# add annotations for rate limit etc.

if TESTING:
    CELERY_ALWAYS_EAGER = True

# Nose
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Logging: Add to existing django logging configuration, except when
# running tests, since nose will capture the log output itself
if not TESTING:
    FORMATTER_SIMPLE_FORMAT = '[%(asctime)s %(levelname)s/%(name)s-%(process)d] %(message)s'
    LOGGING = {
        'version': 1,
        'formatters': {
            'simple': {
                'format': FORMATTER_SIMPLE_FORMAT,
                }
            },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                }
            },
        'loggers': {
            'freezr': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': False,
                }
            }
        }

# REST framework settings
REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}

import freezr.celery
