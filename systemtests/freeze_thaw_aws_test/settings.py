# Get all other defaults directly from freezr.settings, but override
# some custom ones.
import os
os.environ['DONT_IMPORT_CELERY'] = 'true'

from freezr.app.settings.development import *

BROKER_URL = 'amqp://guest@localhost/freezr_testing'
CELERYBEAT_SCHEDULER = None #disable periodic tasks during testing

# move db to our location, not in src tree
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

#print("BROKER_URL = {0}".format(BROKER_URL))


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
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': 'freezr.log',
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

import freezr.backend.celery
