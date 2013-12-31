# Get all other defaults directly from freezr.settings, but override
# some custom ones.
import os
os.environ['DONT_IMPORT_CELERY'] = 'true'

from freezr.app.settings.development import *  # noqa

BROKER_URL = 'amqp://guest@localhost/freezr_testing'
CELERYBEAT_SCHEDULER = None  # disable periodic tasks during testing

# move db to our location, not in src tree
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     }
# }

#print("BROKER_URL = {0}".format(BROKER_URL))

# Two version of logging configuration. One for server-under-test and
# another to configure the actual unit tests (which will indirectly
# load this file, thus causing django config to set the logging
# paremeters **from here**).

if 'NOSE' not in os.environ:
    # Server-under-test logging configuration. Log to stderr
    # (streamhandler).
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
                'formatter': 'simple',
                'class': 'logging.StreamHandler',
                }
            },
        'loggers': {
            'freezr': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
                },
            'freeze_thaw_aws_test': {
                'handlers': ['console'],
                'level': 'DEBUG',
                'propagate': True,
                }
            }
        }
else:
    # Running under unit test, let nosetests capture the output.
    LOGGING = {
        'version': 1
        }

import freezr.backend.celery  # noqa
