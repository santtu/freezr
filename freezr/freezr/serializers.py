from rest_framework import serializers
from freezr.models import *
import logging

log = logging.getLogger('freezr.serializers')

class DomainSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active', 'accounts')

class AccountSerializer(serializers.HyperlinkedModelSerializer):
    regions = serializers.Field()

    class Meta:
        model = Account
        fields = ('id', 'domain', 'name', 'access_key',
                  'active', 'projects', 'regions',
                  'instances')

class CommaStringListField(util.Logger, serializers.WritableField):
    def to_native(self, obj):
        self.log.debug("to_native: self=%r obj=%r", self, obj)
        return list(set(obj.split(",")))

    def from_native(self, data):
        self.log.debug("from_native: self=%r data=%r", self, data)
        return ",".join(data)

class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    picked_instances = serializers.Field()
    saved_instances = serializers.Field()
    regions = CommaStringListField(source='_regions')

    class Meta:
        model = Project
        fields = ('id', 'state', 'account',
                  'regions',
                  'name', 'description',
                  'elastic_ips', 'pick_filter', 'save_filter',
                  'picked_instances', 'saved_instances')

class InstanceSerializer(serializers.HyperlinkedModelSerializer):
    tags = serializers.Field()

    class Meta:
        model = Instance
        fields = ('account', 'instance_id', 'region', 'vpc_id',
                  'store', 'state', 'tags')

    def transform_tags(self, obj, value):
        return {tag.key: tag.value for tag in obj.tags.all()}
