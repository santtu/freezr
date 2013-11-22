from rest_framework import serializers
from freezr.models import *
import logging

log = logging.getLogger('freezr.serializers')

class CommaStringListField(util.Logger, serializers.WritableField):
    def to_native(self, obj):
        self.log.debug("to_native: self=%r obj=%r", self, obj)
        return list(set(obj.split(",")))

    def from_native(self, data):
        self.log.debug("from_native: self=%r data=%r", self, data)
        return ",".join(data)

class LogEntrySerializer(serializers.ModelSerializer):
    user_id = serializers.Field(source='user.id')
    user = serializers.Field(source='user.username')

    class Meta:
        model = LogEntry
        fields = ('type', 'time', 'message', 'details', 'user_id', 'user')

class DomainSerializer(serializers.HyperlinkedModelSerializer):
    log_entries = LogEntrySerializer(many=True)

    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active', 'accounts', 'log_entries', 'domain', 'url')

class AccountSerializer(serializers.HyperlinkedModelSerializer):
    regions = serializers.Field()
    updated = serializers.Field() # no user-initiated updates on this field
    log_entries = LogEntrySerializer(many=True)

    class Meta:
        model = Account
        fields = ('id', 'domain', 'name', 'access_key',
                  'active', 'projects', 'regions',
                  'instances', 'updated', 'log_entries', 'url')

class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    picked_instances = serializers.Field()
    saved_instances = serializers.Field()
    regions = CommaStringListField(source='_regions')
    log_entries = LogEntrySerializer(many=True)

    class Meta:
        model = Project
        fields = ('id', 'state', 'account',
                  'regions',
                  'name', 'description',
                  'elastic_ips', 'pick_filter', 'save_filter',
                  'picked_instances', 'saved_instances',
                  'log_entries', 'url')

class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.Field()

    class Meta:
        model = Instance
        fields = ('account', 'instance_id', 'region', 'vpc_id',
                  'store', 'state', 'tags', 'url')

    def transform_tags(self, obj, value):
        return {tag.key: tag.value for tag in obj.tags.all()}
