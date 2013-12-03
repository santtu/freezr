# freezr.app.urls
import django.conf.urls as urls
from django.views.defaults import server_error
from django.contrib import admin
import freezr.app.admin
import logging
from django.conf import settings

log = logging.getLogger('freezr.app.urls')

freezr.app.admin.setup()

urlpatterns = urls.patterns(
    '',
    urls.url(r'^admin/', urls.include(admin.site.urls)),
    )

if 'freezr.api' in settings.INSTALLED_APPS:
    import freezr.api.urls
    urlpatterns += freezr.api.urls.urlpatterns

if 'freezr.ui' in settings.INSTALLED_APPS:
    import freezr.ui.urls
    urlpatterns += freezr.ui.urls.urlpatterns

def handler500(request):
    log.exception('Internal server error on %s %s',
                  request.method, request.get_full_path())
    return server_error(request)
