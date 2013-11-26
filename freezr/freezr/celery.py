from __future__ import absolute_import
import os

from celery import Celery
from django.conf import settings

#print("DJANGO_SETTINGS_MODULE = {0}".format(os.environ.get('DJANGO_SETTINGS_MODULE')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'freezr.settings')

app = Celery('freezr')
app.config_from_object('django.conf:settings')

#app.autodiscover_tasks(settings.INSTALLED_APPS, related_name='tasks')
