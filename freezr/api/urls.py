from __future__ import absolute_import
import django.conf.urls as urls
from django.views.defaults import server_error
from .views import *
from rest_framework import viewsets, routers
import logging

log = logging.getLogger('freezr.api.urls')

router = routers.DefaultRouter()
router.register(r'domain', DomainViewSet)
router.register(r'account', AccountViewSet)
router.register(r'project', ProjectViewSet)
router.register(r'instance', InstanceViewSet)

urlpatterns = urls.patterns(
    '',
    urls.url(r'^api/', urls.include(router.urls))
    )
