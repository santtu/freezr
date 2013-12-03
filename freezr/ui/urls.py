from __future__ import absolute_import
from django.conf.urls import url, patterns
import logging
from . import views

log = logging.getLogger('freezr.ui.urls')

urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index'),
    )
