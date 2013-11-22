from freezr.models import *
from freezr.serializers import *
import freezr.tasks as tasks
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from rest_framework import generics
from rest_framework import viewsets, routers
import freezr.util as util

class DomainViewSet(viewsets.ModelViewSet):
    model = Domain
    serializer_class = DomainSerializer

class AccountViewSet(util.Logger, viewsets.ModelViewSet):
    model = Account
    serializer_class = AccountSerializer

    @action()
    def refresh(self, request, pk):
        self.log.debug("refresh: self=%r request=%r pk=%r",
                       self, request, pk)

        # TODO: Access control
        account = Account.objects.get(pk=pk)

        # use older_than to cause some throttling
        tasks.refresh_account.delay(pk, older_than=30)
        return Response()

class ProjectViewSet(viewsets.ModelViewSet):
    model = Project
    serializer_class = ProjectSerializer

class InstanceViewSet(viewsets.ReadOnlyModelViewSet):
    model = Instance
    serializer_class = InstanceSerializer
