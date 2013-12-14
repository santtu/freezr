from __future__ import absolute_import
import django.conf.urls as urls
from .views import (DomainViewSet, AccountViewSet,
                    ProjectViewSet, InstanceViewSet)
from rest_framework import routers
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
