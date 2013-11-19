from django.contrib import admin
from freezr.models import *

admin.autodiscover()

admin.site.register(Domain)
admin.site.register(Account)

class InstanceTagFilterAdminInline(admin.TabularInline):
    model = InstanceTagFilter

class SaveTagFilterAdminInline(admin.TabularInline):
    model = SaveTagFilter

class ProjectAdmin(admin.ModelAdmin):
    inlines = (InstanceTagFilterAdminInline, SaveTagFilterAdminInline)

admin.site.register(Project, ProjectAdmin)
