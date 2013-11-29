#from django.conf.urls import patterns, include, url
import django.conf.urls as urls
from django.views.defaults import server_error
from freezr.views import *
from rest_framework import viewsets, routers
from django.contrib import admin
import freezr.admin
import logging

log = logging.getLogger('freezr.urls')

router = routers.DefaultRouter()
router.register(r'domain', DomainViewSet)
router.register(r'account', AccountViewSet)
router.register(r'project', ProjectViewSet)
router.register(r'instance', InstanceViewSet)

freezr.admin.setup()

urlpatterns = urls.patterns(
    '',

    urls.url(r'^admin/', urls.include(admin.site.urls)),
    urls.url(r'^api/', urls.include(router.urls))
    )

def handler500(request):
    log.exception('Internal server error on %s %s',
                  request.method, request.get_full_path())
    return server_error(request)
