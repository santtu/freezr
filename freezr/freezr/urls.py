from django.conf.urls import patterns, include, url
from django.contrib import admin
from freezr.models import *
from freezr import views

admin.autodiscover()

admin.site.register(Domain)
admin.site.register(Account)
#admin.site.register(Project)

class InstanceTagFilterAdminInline(admin.TabularInline):
    model = InstanceTagFilter

class SavedTagFilterAdminInline(admin.TabularInline):
    model = SavedTagFilter

class ProjectAdmin(admin.ModelAdmin):
    inlines = (InstanceTagFilterAdminInline, SavedTagFilterAdminInline)

admin.site.register(Project, ProjectAdmin)

urlpatterns = patterns(
    '',
    ## Examples:
    # url(r'^$', 'freezr.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),

    url(r'^api/domain/$', views.DomainList.as_view()),
    url(r'^api/domain/(?P<pk>[0-9]+)$', views.DomainDetail.as_view()),
    url(r'^api/account/$', views.AccountList.as_view()),
    url(r'^api/account/(?P<pk>[0-9]+)$', views.AccountDetail.as_view()),
    )
