from __future__ import absolute_import
from django.contrib import admin, auth
import django.contrib.auth.admin  # noqa, needed for auth.admin to work
from freezr.core.models import (Account, ProjectGroupRelation,
                                LogEntry, Domain, Project)
import logging

log = logging.getLogger('freezr.admin')


class ProjectGroupRelationInline(admin.TabularInline):
    model = ProjectGroupRelation


class GroupAdmin(auth.admin.GroupAdmin):
    """Extend the contrib GroupAdmin to include our project group
    relation to the admin editor."""
    inlines = (ProjectGroupRelationInline,)


class ProjectAdmin(admin.ModelAdmin):
    inlines = (ProjectGroupRelationInline,)


class LogEntryAdmin(admin.ModelAdmin):
    readonly_fields = LogEntry._meta.get_all_field_names()


def setup():
    admin.autodiscover()
    admin.site.register(Domain)
    admin.site.register(Account)
    admin.site.register(Project, ProjectAdmin)
    admin.site.register(LogEntry, LogEntryAdmin)
    # Switch the default auth.admin.GroupAdmin and UserAdmin to our
    # own frezr.admin.GroupAdmin and UserAdmin classes.

    # Note: the user admin inline does not work as I wish it
    # should. It should allow you to select from existing domains, and
    # add lines and remove them. Using Inline inlines the whole
    # thing. OTOH, I don't know how to get the field to display in
    # there regularly, so I'll settle for the time being only being
    # able to edit domain ownership via the Domain object itself.

    # admin.site.unregister(auth.models.User)
    admin.site.unregister(auth.models.Group)
    # admin.site.register(auth.models.User, UserAdmin)
    admin.site.register(auth.models.Group, GroupAdmin)
