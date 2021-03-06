from __future__ import absolute_import
import logging
from freezr.core.models import Account, Project, Instance
import pytz
from rest_framework import test
from django.core.urlresolvers import reverse
from itertools import chain
from datetime import datetime
from .util import AwsMockFactory, ImmediateAwsMock, with_aws, Mixin
from django.utils import timezone
from datetime import timedelta
from django.conf import settings

log = logging.getLogger(__file__)


def flatu(items):
    """flat unique"""
    return list(set(chain.from_iterable(items)))


class TestREST(Mixin, test.APITestCase):
    fixtures = ('rest_tests',)

    def setUp(self):
        self.account = Account.objects.get(pk=1)
        self.saved_cloud_backend = settings.FREEZR_CLOUD_BACKEND

    def tearDown(self):
        settings.FREEZR_CLOUD_BACKEND = self.saved_cloud_backend

    def testListDomains(self):
        response = self.client.get(reverse('domain-list'))

        self.assertEqual(2, len(response.data))
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'name', 'description', 'active',
                               'accounts', 'log_entries', 'domain'))

    def testGetDomain(self):
        response = self.client.get(reverse('domain-detail', args=[1]))
        self.assertSimilar(response.data,
                           {'id': 1,
                            'name': u'Test domain no. 1',
                            'description': u'',
                            'active': True,
                            'accounts': [1, 2],
                            'log_entries': [],
                            'domain': u'test.local'})
        response = self.client.get(reverse('domain-detail', args=[2]))
        self.assertSimilar(response.data,
                           {'id': 2,
                            'name': u'Test domain no. 2',
                            'description': u'',
                            'active': True,
                            'accounts': [3],
                            'log_entries': [],
                            'domain': u'domain.com'})

    def testListAccounts(self):
        response = self.client.get(reverse('account-list'))

        self.assertEqual(len(response.data), 3)
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'domain', 'name', 'access_key', 'active',
                               'projects', 'regions', 'instances', 'updated',
                               'log_entries'))

    def testGetAccount(self):
        response = self.client.get(reverse('account-detail', args=[1]))
        self.assertSimilar(response.data,
                           {'id': 1,
                            'domain': 1,
                            'name': u'Test account no. 1.1',
                            'access_key': u'123456',
                            'active': True,
                            'projects': [1],
                            'regions': [u'us-east-1',
                                        u'ap-northeast-1',
                                        u'sa-east-1',
                                        u'ap-southeast-1',
                                        u'ap-southeast-2',
                                        u'us-west-2',
                                        u'us-west-1',
                                        u'eu-west-1'],
                            'instances': [1, 2],
                            'updated': None,
                            'log_entries': []})

        response = self.client.get(reverse('account-detail', args=[2]))
        self.assertSimilar(response.data,
                           {'id': 2,
                            'domain': 1,
                            'name': u'Test account no. 1.2',
                            'access_key': u'567890',
                            'active': True,
                            'projects': [],
                            'regions': [],
                            'instances': [],
                            'updated': None,
                            'log_entries': []})

        response = self.client.get(reverse('account-detail', args=[3]))
        self.assertSimilar(response.data,
                           {'id': 3,
                            'domain': 2,
                            'name': u'Test account no. 2.1',
                            'access_key': u'fnord',
                            'active': True,
                            'projects': [2],
                            'regions': [u'us-east-1',
                                        u'ap-northeast-1',
                                        u'sa-east-1',
                                        u'ap-southeast-1',
                                        u'ap-southeast-2',
                                        u'us-west-2',
                                        u'us-west-1',
                                        u'eu-west-1'],
                            'instances': [3, 4, 5],
                            'updated': None,
                            'log_entries': [{'type': u'info',
                                             'time': datetime(2013, 11, 22,
                                                              10, 0, 53,
                                                              349330,
                                                              tzinfo=pytz.utc),
                                             'message': u'Sample log entry',
                                             'details': None,
                                             'user_id': None,
                                             'user': None}]})

    def testListProjects(self):
        response = self.client.get(reverse('project-list'))

        self.assertEqual(len(response.data), 2)
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'state', 'account', 'regions', 'name',
                               'description', 'elastic_ips', 'pick_filter',
                               'save_filter', 'terminate_filter',
                               'picked_instances', 'saved_instances',
                               'terminated_instances', 'skipped_instances',
                               'log_entries', 'state_updated'))

    def testGetProject(self):
        response = self.client.get(reverse('project-detail', args=[1]))
        self.assertSimilar(response.data,
                           {'id': 1,
                            'state': u'init',
                            'account': 1,
                            'regions': [u'us-east-1',
                                        u'ap-northeast-1',
                                        u'sa-east-1',
                                        u'ap-southeast-1',
                                        u'ap-southeast-2',
                                        u'us-west-2',
                                        u'us-west-1',
                                        u'eu-west-1'],
                            'name': u'Test project no. 1.1.1',
                            'description': u'',
                            'elastic_ips': [],
                            'pick_filter': u'tag[project111]',
                            'save_filter': u'tag[save]',
                            'terminate_filter': u'tag[terminate]',
                            'picked_instances': [2, 1],
                            'saved_instances': [1],
                            'skipped_instances': [],
                            'terminated_instances': [2],
                            'log_entries': [],
                            'state_updated':
                            datetime(2013, 12, 2, 12, 12, 12,
                                     tzinfo=pytz.utc),
                            })
        response = self.client.get(reverse('project-detail', args=[2]))
        self.assertSimilar(response.data,
                           {'id': 2,
                            'state': u'init',
                            'account': 3,
                            'regions': [u'us-east-1',
                                        u'ap-northeast-1',
                                        u'sa-east-1',
                                        u'ap-southeast-1',
                                        u'ap-southeast-2',
                                        u'us-west-2',
                                        u'us-west-1',
                                        u'eu-west-1'],
                            'name': u'Test project no. 2.1.1',
                            'description': u'',
                            'elastic_ips': [],
                            'pick_filter': u'tag[project211]',
                            'save_filter': u'true',
                            'terminate_filter': u'',
                            'picked_instances': [5, 3],
                            'saved_instances': [5, 3],
                            'skipped_instances': [],
                            'terminated_instances': [],
                            'log_entries': [],
                            'state_updated':
                            datetime(2013, 12, 2, 12, 12, 12,
                                     tzinfo=pytz.utc),
                            })

    # Note that this absolutely requires that you either have set up a
    # testing celery with the same test database as this test is using
    # (yeah, right), or have set CELERY_ALWAYS_EAGER = True in
    # settings.

    def testRefreshAccount(self):
        factory = AwsMockFactory(ImmediateAwsMock)
        with with_aws(factory):
            log.debug("regions=%r", Account.objects.get(pk=1).regions)

            old = Account.objects.get(pk=1).updated
            response = self.client.post(reverse('account-refresh', args=[1]))
            self.assertEqual(response.status_code, 202)
            self.assertEqual(len(factory.aws_list), 1)
            self.assertEqual(len(factory.aws.calls), 8)
            self.assertNotEqual(Account.objects.get(pk=1).updated, old)

        factory = AwsMockFactory(ImmediateAwsMock)
        with with_aws(factory):
            old = Account.objects.get(pk=3).updated
            response = self.client.post(reverse('account-refresh', args=[3]))
            self.assertEqual(response.status_code, 202)
            self.assertEqual(len(factory.aws_list), 1)
            self.assertEqual(len(factory.aws.calls), 8)
            self.assertNotEqual(Account.objects.get(pk=3).updated, old)

    def testRefreshInactiveAccount(self):
        self.account.active = False
        self.account.save()

        factory = AwsMockFactory(ImmediateAwsMock)
        with with_aws(factory):
            response = self.client.post(reverse('account-refresh', args=[1]))
            self.assertEqual(response.status_code, 403)
            self.assertEqual(len(factory.aws_list), 0)

    ## Note: It is not possible to really test refresh with
    ## transitioning states, since the test suite will run all tasks
    ## synchronously this would cause tasks.refresh_instance to
    ## recursively call itself.

    # def testRefreshAccountTransitioningInstances(self):
    #     pass

    def testFreezeAccount(self):
        factory = AwsMockFactory(ImmediateAwsMock)

        # This should fail with 409 since the project is in init state
        with with_aws(factory):
            response = self.client.post(reverse('project-freeze', args=[1]))
            self.assertEqual(response.status_code, 409)
            self.assertEqual(factory.aws_list, [])
            self.assertTrue('error' in response.data)
            self.assertEqual(response.data['error'],
                             'Project state is not valid for freezing')

        for p in Project.objects.all():
            p.state = 'running'
            p.save()

        self.account.updated = timezone.now() - timedelta(days=1)
        self.account.save()

        with with_aws(factory):
            response = self.client.post(reverse('project-freeze', args=[1]))
            self.assertEqual(response.status_code, 202)
            self.assertEqual(len(factory.aws_list), 3)
            self.assertTrue('state' in response.data)
            self.assertEqual(response.data['state'], 'freezing')

            # Combine calls from all AWS mocks
            calls = chain.from_iterable([a.calls for a in factory.aws_list])
            calls = list(calls)

            # Collapse names of called methods into single list
            names = [c[0] for c in calls]
            names = reduce(lambda a, b: a if a[-1] == b else a + [b],
                           names[1:], [names[0]])

            log.debug("calls=%r", calls)

            # This is the expected call sequence. Actually we'd want
            # to do it as a regular expression refresh_region
            # (terminate_instance|freeze_instance)+ refresh_region but
            # oh well. Don't make test cases too elaborate.
            self.assertTrue(
                (names == ['refresh_region', 'terminate_instance',
                           'freeze_instance', 'refresh_region'] or
                 names == ['refresh_region', 'freeze_instance',
                           'terminate_instance', 'refresh_region']),
                "%r is not expected "
                "refresh+freeze/terminate+refresh sequence" % (names,))

    def testThawAccount(self):
        factory = AwsMockFactory(ImmediateAwsMock)

        # This should fail with 409 since the project is in init state
        with with_aws(factory):
            response = self.client.post(reverse('project-thaw', args=[1]))
            self.assertEqual(response.status_code, 409)
            self.assertEqual(factory.aws_list, [])
            self.assertTrue('error' in response.data)
            self.assertEqual(response.data['error'],
                             'Project state is not valid for thawing')

        for p in Project.objects.all():
            p.state = 'frozen'
            p.save()

        # set instances to stopped state
        for i in Instance.objects.all():
            i.state = 'stopped'
            i.save()

        # we should get refresh_region calls regardless of regular
        # rules about older_than updates
        self.account.updated = timezone.now() - timedelta(days=1)
        self.account.save()

        with with_aws(factory):
            response = self.client.post(reverse('project-thaw', args=[1]))
            self.assertEqual(response.status_code, 202)
            self.assertEqual(len(factory.aws_list), 3)
            self.assertTrue('state' in response.data)
            self.assertEqual(response.data['state'], 'thawing')
            # the actual project should now be in running state due to
            # synchronous task, the above response should reflect the
            # state when the task wasn't yet actually run
            self.assertEqual(Project.objects.get(pk=1).state, "running")

            # Combine calls from all AWS mocks
            calls = chain.from_iterable([a.calls for a in factory.aws_list])
            calls = list(calls)

            log.debug("calls=%r", calls)

            # Collapse names of called methods into single list
            names = [c[0] for c in calls]
            names = reduce(lambda a, b: a if a[-1] == b else a + [b],
                           names[1:], [names[0]])

            self.assertEqual(names, ['refresh_region', 'thaw_instance',
                                     'refresh_region'])
