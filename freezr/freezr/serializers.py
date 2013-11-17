from rest_framework import serializers
from freezr.models import *

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = ('id', 'name', 'description', 'active')

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ('id', 'domain', 'name',
                  'access_key', 'active')
