from freezr.models import *
from freezr.serializers import *
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import generics
from rest_framework import viewsets, routers

# class DomainList(APIView):
#     def get(self, request, format=None):
#         domains = Domain.objects.all()
#         serializer = DomainSerializer(domains, many=True)
#         return Response(serializer)

# class DomainDetail(APIView):
#     def get_object(self, pk):
#         try:
#             return Domain.objects.get(pk=pk)
#         except Domain.DoesNotExist:
#             raise Http404

#     def get(self, request, pk, format=None):
#         domain = self.get_object(pk)
#         serializer = DomainSerializer(domain)
#         return Response(serializer.data)

# class AccountList(generics.ListAPIView):
#     queryset = Account.objects.all()
#     serializer_class = AccountSerializer

# class AccountDetail(generics.RetrieveUpdateDestroyAPIView):
#     queryset = Account.objects.all()
#     serializer_class = AccountSerializer

class DomainViewSet(viewsets.ModelViewSet):
    model = Domain
    serializer_class = DomainSerializer

class AccountViewSet(viewsets.ModelViewSet):
    model = Account
    serializer_class = AccountSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    model = Project
    serializer_class = ProjectSerializer

# class TagFilterViewSet(viewsets.ModelViewSet):
#     model = TagFilter
#     serializer_class = TagFilterSerializer

# class InstanceTagFilterViewSet(viewsets.ModelViewSet):
#     model = InstanceTagFilter
#     serializer_class = InstanceTagFilterSerializer

# class SaveTagFilterViewSet(viewsets.ModelViewSet):
#     model = SaveTagFilter
#     serializer_class = SaveTagFilterSerializer
