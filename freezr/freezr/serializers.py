from rest_framework import serializers
from freezr.models import *

class DomainSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active', 'accounts')

class AccountSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account
        fields = ('id', 'domain', 'name', 'access_key', 'active', 'projects')

class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'state', 'account', 'region', 'vpc_id',
                  'name', 'description',
                  'elastic_ips', 'pick_filter', 'save_filter')

# class TagFilterSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = TagFilter
#         fields = ('key', 'value', 'type', 'project')

# class InstanceTagFilterSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = InstanceTagFilter
#         fields = ('key', 'value', 'project')

# class SaveTagFilterSerializer(serializers.HyperlinkedModelSerializer):
#     class Meta:
#         model = SaveTagFilter
#         fields = ('key', 'value', 'project')
