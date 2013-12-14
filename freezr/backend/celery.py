from __future__ import absolute_import

from celery import Celery

app = Celery('freezr')
app.config_from_object('django.conf:settings')
