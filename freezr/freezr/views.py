from freezr.models import *
from freezr.serializers import *
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework import viewsets, routers

class DomainViewSet(viewsets.ModelViewSet):
    model = Domain
    serializer_class = DomainSerializer

class AccountViewSet(viewsets.ModelViewSet):
    model = Account
    serializer_class = AccountSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    model = Project
    serializer_class = ProjectSerializer

class InstanceViewSet(viewsets.ReadOnlyModelViewSet):
    model = Instance
    serializer_class = InstanceSerializer
