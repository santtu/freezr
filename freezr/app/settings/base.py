from datetime import timedelta

# base freezr settings, defining the absolute minimum required for
# freezr to successfully work (it is up to you to fill the rest)
# INSTALLED_APPS = (
#     'rest_framework',
#     'freezr'
#     # djcelery isn't require to submit jobs, it is required for the
#     # node to run those tasks..
#     )

ROOT_URLCONF = 'freezr.app.urls'
WSGI_APPLICATION = 'freezr.app.wsgi.application'
ATOMIC_REQUESTS = True

CELERY_IMPORTS = ('freezr.backend.celery', 'freezr.backend.tasks')
CELERY_TASK_RESULT_EXPIRES = 600  # 10 minutes
CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
CELERY_TASK_PUBLISH_RETRY = True
CELERY_TRACK_STARTED = True

CELERYBEAT_SCHEDULE = {
    'refresh-accounts': {
        'task': 'freezr.backend.tasks.refresh',
        'schedule': timedelta(minutes=10),
        },
    'reissue-operations': {
        'task': 'freezr.backend.tasks.reissue_operations',
        'schedule': timedelta(minutes=10),
        }
}

# REST framework settings
REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'

#import freezr.celery
