from freezr.models import *
from freezr.serializers import *
import freezr.tasks as tasks
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework import status
from rest_framework import generics
from rest_framework import viewsets, routers
import freezr.util as util
import traceback

class BaseViewSet(util.Logger, viewsets.ModelViewSet):
    def handle_exception(self, exc):
        # Just ignore some exceptions which are communicating normal
        # cases up the chain.
        if not isinstance(exc, (MethodNotAllowed, Http404)):
            self.log.exception('Handling request %s %s',
                               self.request.method, self.request.get_full_path())

        return super(BaseViewSet, self).handle_exception(exc)

class DomainViewSet(BaseViewSet):
    model = Domain
    serializer_class = DomainSerializer

class AccountViewSet(BaseViewSet):
    model = Account
    serializer_class = AccountSerializer

    @action()
    @util.log_error(Account)
    def refresh(self, request, pk):
        self.log.debug("refresh: self=%r request=%r pk=%r",
                       self, request, pk)

        # TODO: Access control
        account = Account.objects.get(pk=pk)

        # use older_than to cause some throttling
        async = tasks.refresh_account.delay(pk, older_than=30)
        return Response({'message': 'Project refresh started',
                         'operation': async.id},
                        status=status.HTTP_202_ACCEPTED)

    def post_save(self, obj, **kwargs):
        super(AccountViewSet, self).post_save(obj, **kwargs)
        self.log.debug("post_save: triggering account %s refresh", obj)
        tasks.refresh_account.apply_async([obj.id], {'older_than': 0},
                                          countdown=5)

class ProjectViewSet(BaseViewSet):
    model = Project
    serializer_class = ProjectSerializer

    # TODO: extend @log_error mechanism either to
    # create/retrieve/update/partial_update/destroy/list methods, or
    # move the whole error logging out of here to somewhere
    # sensible. (OTOH, if we want to have errors linked to the correct
    # object, we need that information somwhere close by...)

    @action()
    @util.log_error(Project)
    def freeze(self, request, pk):
        self.log.debug("freeze: self=%r request=%r pk=%r",
                       self, request, pk);
        project = Project.objects.get(pk=pk)

        if project.state != 'running':
            return Response({'error': 'Project state is not valid for freezing'},
                            status=status.HTTP_409_CONFLICT)

        # Do a forced refresh on the account just before freeze so we
        # have as up-to-date information as possible. (Freeze operates
        # based on our knowledge of the account.)
        async = (
            tasks.refresh_account.si(project.account.id, older_than=0) |
            tasks.freeze_project.si(project.id) |
            tasks.refresh_account.si(project.account.id, older_than=0)
            ).delay()

        #tasks.freeze_project.delay(project.id)
        self.log.debug("freeze: async=%r", async)

        return Response({'message': 'Project freezing started',
                         'operation': async.id},
                        status=status.HTTP_202_ACCEPTED)

    @action()
    @util.log_error(Project)
    def thaw(self, request, pk):
        self.log.debug("thaw: self=%r request=%r pk=%r",
                       self, request, pk)
        project = Project.objects.get(pk=pk)

        if project.state != 'frozen':
            return Response({'error': 'Project state is not valid for thawing'},
                            status=status.HTTP_409_CONFLICT)

        # Again, do a forced refresh before starting the thaw
        # operation.
        async = (
            tasks.refresh_account.si(project.account.id, older_than=0) |
            tasks.thaw_project.si(project.id) |
            tasks.refresh_account.si(project.account.id, older_than=0)
            ).delay()

        self.log.debug("freeze: async=%r", async)

        return Response({'message': 'Project thawing started',
                         'operation': async.id},
                        status=status.HTTP_202_ACCEPTED)

class InstanceViewSet(viewsets.ReadOnlyModelViewSet):
    model = Instance
    serializer_class = InstanceSerializer
