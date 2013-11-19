from django.conf.urls import patterns, include, url
from freezr.views import *
from rest_framework import viewsets, routers
from django.contrib import admin

router = routers.DefaultRouter()
router.register(r'domain', DomainViewSet)
router.register(r'account', AccountViewSet)
router.register(r'project', ProjectViewSet)
#router.register(r'tag-filter', TagFilterViewSet)

urlpatterns = patterns(
    '',

    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include(router.urls))
    )
