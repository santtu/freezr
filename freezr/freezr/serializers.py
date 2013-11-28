from rest_framework import serializers
from freezr.models import *
import logging
from freezr.celery.tasks import refresh_account, dispatch

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
        return list(set(obj.split(",")))

    def from_native(self, data):
        return ",".join(data)

class LogEntrySerializer(serializers.ModelSerializer):
    user_id = serializers.Field(source='user.id')
    user = serializers.Field(source='user.username')

    class Meta:
        model = LogEntry
        fields = ('type', 'time', 'message', 'details', 'user_id', 'user')

class DomainSerializer(serializers.HyperlinkedModelSerializer):
    log_entries = LogEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active', 'accounts',
                  'log_entries', 'domain', 'url')

class AccountSerializer(util.Logger, ImmutableMixin,
                        serializers.HyperlinkedModelSerializer):
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
                  'instances', 'updated', 'log_entries', 'url')
        immutable_fields = ('domain',)

class ProjectSerializer(util.Logger, ImmutableMixin,
                        serializers.HyperlinkedModelSerializer):
    picked_instances = serializers.HyperlinkedRelatedField(
        many=True, view_name='instance-detail', read_only=True)

    saved_instances = serializers.HyperlinkedRelatedField(
        many=True, view_name='instance-detail', read_only=True)

    terminated_instances = serializers.HyperlinkedRelatedField(
        many=True, view_name='instance-detail', read_only=True)

    skipped_instances = serializers.HyperlinkedRelatedField(
        many=True, view_name='instance-detail', read_only=True)

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

        # Check if account's region set grows, trigger refresh if so
        account = instance.account if instance else attrs['account']
        request_regions = ((attrs.get('_regions').split(","))
                           if attrs.get('_regions', '')
                           else [])
        instance_regions = (set(request_regions) |
                            set(instance.regions if instance else []))
        account_regions = set(account.regions)

        if not (instance_regions <= account_regions):
            self.log.info('Detected new regions from project %s to account %s, '
                          'triggering account refresh: %r',
                          instance if instance else attrs.get('name', 'unknown'),
                          account,
                          instance_regions - account_regions)

            dispatch(refresh_account.si(account.id, older_than=0),
                     countdown=10)

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
                  'log_entries', 'url')
        immutable_fields = ('account',)

class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.Field()

    class Meta:
        model = Instance
        fields = ('account', 'instance_id', 'region', 'vpc_id',
                  'store', 'state', 'tags', 'url')

    def transform_tags(self, obj, value):
        return {tag.key: tag.value for tag in obj.tags.all()}
