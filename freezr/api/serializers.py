from rest_framework import serializers
from freezr.core.models import *
from freezr.common.util import separator_split
import logging
from freezr.backend.tasks import refresh_account, dispatch
from itertools import chain
from collections import Counter

log = logging.getLogger('freezr.serializers')

class ImmutableMixin(object):
    def restore_object(self, attrs, instance=None):
        if instance:
            for field in getattr(self.Meta, 'immutable_fields', []):
                if field in attrs:
                    self.log.debug("Deleting immutable field %r=%r "
                                   "on update of %s",
                                   field, attrs[field], instance)
                    del attrs[field]

        return super(ImmutableMixin, self).restore_object(attrs,
                                                          instance=instance)

class CommaStringListField(util.Logger, serializers.WritableField):
    def to_native(self, obj):
        return list(set(separator_split(obj, ",")))

    def from_native(self, data):
        return ",".join(data)

class LogEntrySerializer(serializers.ModelSerializer):
    user_id = serializers.Field(source='user.id')
    user = serializers.Field(source='user.username')

    class Meta:
        model = LogEntry
        fields = ('type', 'time', 'message', 'details', 'user_id', 'user')

#class DomainSerializer(serializers.HyperlinkedModelSerializer):
class DomainSerializer(serializers.ModelSerializer):
    log_entries = LogEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active', 'accounts',
                  'log_entries', 'domain',
                  #'url',
                  )


class AccountSerializer(util.Logger, ImmutableMixin,
                        serializers.ModelSerializer):
#                        serializers.HyperlinkedModelSerializer):
    regions = serializers.Field()
    updated = serializers.Field() # no user-initiated updates on this field
    log_entries = LogEntrySerializer(many=True, read_only=True)
    secret_key = serializers.WritableField(required=False)

    # def restore_fields(self, data, files):
    #     self.log.debug('restore_fields: data=%r files=%r',
    #                    data, files)
    #     return super(AccountSerializer, self).restore_fields(data, files)

    # def restore_object(self, attrs, instance=None):
    #     ret = super(AccountSerializer, self).restore_object(attrs,
    # instance=instance)
    #     self.log.debug("restore_object: attrs=%r instance=%r => %r",
    #                    attrs, instance, ret)
    #     return ret

    # def from_native(self, data, files):
    #     self.log.debug("from_native: data=%r files=%r", data, files)
    #     return super(AccountSerializer, self).from_native(data, files)
    def restore_object(self, attrs, instance=None):
        # Cannot change active if any of the projects are in a
        # transitioning state.
        if (instance and 'active' in attrs and
            attrs['active'] != instance.active):
            for project in instance.projects.all():
                if project.state in ('freezing', 'thawing'):
                    self._errors['active'] = [
                        'Cannot change account active state while '
                        'projects are in a transitioning state'
                        ]
                    self.log.error('tried to change active status of account'
                                   '%s while projects transitioning',
                                   instance)
                    return

        if instance:
            self.log.debug("Account %d update, active=%r => %r",
                           instance.id, instance.active,
                           attrs.get('active', None))

        return super(AccountSerializer, self).restore_object(attrs,
                                                             instance=instance)

    def to_native(self, obj):
        """Remove secret_access_key from response, it is write-only
        field."""
        ret = super(AccountSerializer, self).to_native(obj)
        del ret['secret_key']
        return ret

    class Meta:
        model = Account
        fields = ('id', 'domain', 'name', 'access_key', 'secret_key',
                  'active', 'projects', 'regions',
                  'instances', 'updated', 'log_entries',
                  #'url',
                  )
        immutable_fields = ('domain',)

class ProjectSerializer(util.Logger, ImmutableMixin,
#                        serializers.HyperlinkedModelSerializer):
                        serializers.ModelSerializer):
    # picked_instances = serializers.HyperlinkedRelatedField(
    #     many=True, view_name='instance-detail', read_only=True)

    # saved_instances = serializers.HyperlinkedRelatedField(
    #     many=True, view_name='instance-detail', read_only=True)

    # terminated_instances = serializers.HyperlinkedRelatedField(
    #     many=True, view_name='instance-detail', read_only=True)

    # skipped_instances = serializers.HyperlinkedRelatedField(
    #     many=True, view_name='instance-detail', read_only=True)

    picked_instances = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True)

    saved_instances = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True)

    terminated_instances = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True)

    skipped_instances = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True)

    regions = CommaStringListField(source='_regions')

    log_entries = LogEntrySerializer(many=True, read_only=True)

    def restore_object(self, attrs, instance=None):
        # Cannot change filters if the project is in active state.
        if instance and instance.state in ('freezing', 'thawing'):
            errors = False

            for field in ('pick_filter', 'save_filter', 'terminate_filter'):
                if field in attrs and attrs[field] != getattr(instance, field):
                    self._errors[field] = [
                        'cannot be modified while project is %s' % (
                            instance.state,)
                        ]
                    errors = True

            if errors:
                return

        # TODO: Most of the logic below should really be in Account
        # class, not here.

        # Need to check if account regions has changed?
        request_regions = instance_regions = set(instance and
                                                 instance.regions or [])

        if '_regions' in attrs:
            request_regions = set(separator_split(attrs['_regions'], ","))

        refresh = False

        # self.log.debug("_request=%r request_regions=%r "
        #                "instance_regions=%r ^ %r",
        #                attrs.get('_regions', None),
        #                request_regions, instance_regions,
        #                request_regions ^ instance_regions)

        # Is there difference between before and after for regions on
        # this instance? For additions that is easy, just check if new
        # regions for instance are currently in all set or not. For
        # removals of regions we actually have to count how many times
        # they are actually used to see whether any of "old" regions
        # drops to zero count.

        if request_regions ^ instance_regions:
            account = instance.account if instance else attrs['account']

            current = Counter(chain.from_iterable([
                        project.regions for project in account.projects.all()
                        ]))

            current_regions = set(current)

            # additions?
            added_regions = list(request_regions - current_regions)
            if added_regions:
                self.log.debug("New regions on account %s detected: %r",
                               account, added_regions)
                refresh = True

            # removals?
            removed = Counter(current)
            removed.subtract(Counter(instance_regions - request_regions))

            # self.log.debug("removed=%r", removed)

            # if any is 0, it has been removed
            removed_regions = [p[0] for p in removed.items() if not p[1]]
            if removed_regions:
                self.log.debug("Removed regions on account %s detected: %r",
                               account, removed_regions)
                refresh = True

        if refresh:
            dispatch(refresh_account.si(account.id, forced=True))
            account.log_entry('Regions changed',
                              details='Added: %s\nRemoved: %s' % (
                    ", ".join(added_regions) or "none",
                    ", ".join(removed_regions) or "none"),
                              type='info')

        return super(ProjectSerializer, self).restore_object(attrs,
                                                             instance=instance)

    class Meta:
        model = Project
        fields = ('id', 'state', 'account',
                  'regions',
                  'name', 'description',
                  'elastic_ips',
                  'pick_filter', 'save_filter', 'terminate_filter',
                  'picked_instances', 'saved_instances',
                  'skipped_instances', 'terminated_instances',
                  'log_entries'
                  #, 'url')
                  )
        immutable_fields = ('account',)

#class InstanceSerializer(serializers.HyperlinkedModelSerializer):
class InstanceSerializer(serializers.ModelSerializer):
    tags = serializers.Field()

    class Meta:
        model = Instance
        fields = ('id', 'account', 'instance_id', 'region', 'vpc_id',
                  'store', 'state', 'tags',
                  #'url',
                  )

    def transform_tags(self, obj, value):
        return {tag.key: tag.value for tag in obj.tags.all()}
