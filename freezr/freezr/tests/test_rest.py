from __future__ import absolute_import
import logging
import time
from freezr.models import Account, Domain, Project, Instance
from django.db.models import Q
import freezr.urls
import pytz
from rest_framework import test
from django.core.urlresolvers import reverse
from rest_framework import status
from itertools import chain
from datetime import datetime
import copy
from .util import MateMockFactory

log = logging.getLogger(__file__)

def flatu(items):
    """flat unique"""
    return list(set(chain.from_iterable(items)))

class TestREST(test.APITestCase):
    fixtures = ('rest_tests',)

    def assertSimilar(self, a, b, msg=None,
                    sets=('regions','projects','accounts')):
        """Compare two dicts understanding that some fields are
        actually sets as lists and should be compared as sets and not
        lists."""
        a = copy.copy(a)
        b = copy.copy(b)

        for k in sets:
            self.assertEqual(k in a, k in b)
            if k in a:
                self.assertSetEqual(set(a.pop(k)), set(b.pop(k)))

        self.assertEqual(a, b, msg)


    def testListDomains(self):
        response = self.client.get(reverse('domain-list'))

        self.assertEqual(2, len(response.data))
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'name', 'description', 'active',
                               'accounts', 'log_entries', 'domain', 'url'))

    def testGetDomain(self):
        response = self.client.get(reverse('domain-detail', args=[1]))
        self.assertSimilar(response.data,
                         {'id': 1,
                          'name': u'Test domain no. 1',
                          'description': u'',
                          'active': True,
                          'accounts': ['http://testserver/api/account/1/',
                                       'http://testserver/api/account/2/'],
                          'log_entries': [],
                          'domain': u'test.local',
                          'url': 'http://testserver/api/domain/1/'})
        response = self.client.get(reverse('domain-detail', args=[2]))
        self.assertSimilar(response.data,
                         {'id': 2,
                          'name': u'Test domain no. 2',
                          'description': u'',
                          'active': True,
                          'accounts': ['http://testserver/api/account/3/'],
                          'log_entries': [],
                          'domain': u'domain.com',
                          'url': 'http://testserver/api/domain/2/'})

    def testListAccounts(self):
        response = self.client.get(reverse('account-list'))

        self.assertEqual(len(response.data), 3)
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'domain', 'name', 'access_key', 'active',
                               'projects', 'regions', 'instances', 'updated',
                               'log_entries', 'url'))

    def testGetAccount(self):
        response = self.client.get(reverse('account-detail', args=[1]))
        self.assertSimilar(response.data,
                         {'id': 1,
                          'domain': 'http://testserver/api/domain/1/',
                          'name': u'Test account no. 1.1',
                          'access_key': u'123456',
                          'active': True,
                          'projects': ['http://testserver/api/project/1/'],
                          'regions': [u'us-east-1',
                                      u'ap-northeast-1',
                                      u'sa-east-1',
                                      u'ap-southeast-1',
                                      u'ap-southeast-2',
                                      u'us-west-2',
                                      u'us-west-1',
                                      u'eu-west-1'],
                          'instances': [],
                          'updated': None,
                          'log_entries': [],
                          'url': 'http://testserver/api/account/1/'})

        response = self.client.get(reverse('account-detail', args=[2]))
        self.assertSimilar(response.data,
                         {'id': 2,
                          'domain': 'http://testserver/api/domain/1/',
                          'name': u'Test account no. 1.2',
                          'access_key': u'567890',
                          'active': True,
                          'projects': [],
                          'regions': [],
                          'instances': [],
                          'updated': None,
                          'log_entries': [],
                          'url': 'http://testserver/api/account/2/'})

        response = self.client.get(reverse('account-detail', args=[3]))
        self.assertSimilar(response.data,
                         {'id': 3,
                          'domain': 'http://testserver/api/domain/2/',
                          'name': u'Test account no. 2.1',
                          'access_key': u'fnord',
                          'active': True,
                          'projects': ['http://testserver/api/project/2/'],
                          'regions': [u'us-east-1',
                                      u'ap-northeast-1',
                                      u'sa-east-1',
                                      u'ap-southeast-1',
                                      u'ap-southeast-2',
                                      u'us-west-2',
                                      u'us-west-1',
                                      u'eu-west-1'],
                          'instances': [],
                          'updated': None,
                          'log_entries': [{'type': u'info',
                                           'time': datetime(2013, 11, 22,
                                                            10, 0, 53,
                                                            349330,
                                                            tzinfo=pytz.utc),
                                           'message': u'Sample log entry',
                                           'details': None,
                                           'user_id': None,
                                           'user': None}],
                          'url': 'http://testserver/api/account/3/'})

    def testListProjects(self):
        response = self.client.get(reverse('project-list'))

        self.assertEqual(len(response.data), 2)
        self.assertItemsEqual(flatu([d.keys() for d in response.data]),
                              ('id', 'state', 'account', 'regions', 'name',
                               'description', 'elastic_ips', 'pick_filter',
                               'save_filter', 'picked_instances',
                               'saved_instances', 'log_entries', 'url'))

    def testGetProject(self):
        response = self.client.get(reverse('project-detail', args=[1]))
        self.assertSimilar(response.data,
                         {'id': 1,
                          'state': u'init',
                          'account': 'http://testserver/api/account/1/',
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
                          'pick_filter': u'',
                          'save_filter': u'',
                          'picked_instances': [],
                          'saved_instances': [],
                          'log_entries': [],
                          'url': 'http://testserver/api/project/1/'})
        response = self.client.get(reverse('project-detail', args=[2]))
        self.assertSimilar(response.data,
                         {'id': 2,
                          'state': u'init',
                          'account': 'http://testserver/api/account/3/',
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
                          'pick_filter': u'',
                          'save_filter': u'',
                          'picked_instances': [],
                          'saved_instances': [],
                          'log_entries': [],
                          'url': 'http://testserver/api/project/2/'})

    # Note that this absolutely requires that you either have set up a
    # testing celery with the same test database as this test is using
    # (yeah, right), or have set CELERY_ALWAYS_EAGER = True in
    # settings.

    def testRefreshAccount(self):
        for a in Account.objects.all():
            log.debug("%s", a)

        import freezr.aws
        old_account = freezr.aws.Account
        try:
            factory = MateMockFactory()
            freezr.aws.Account = factory

            log.debug("regions=%r", Account.objects.get(pk=1).regions)

            old = Account.objects.get(pk=1).updated
            response = self.client.post(reverse('account-refresh', args=[1]))
            log.debug("response=%r factory=%r factory.mates=%r "
                      "factory.mate.calls=%r",
                      response, factory, factory.mates, factory.mate.calls)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(factory.mates), 1)
            self.assertEqual(len(factory.mate.calls), 8)
            self.assertNotEqual(Account.objects.get(pk=1).updated, old)

            factory = MateMockFactory()
            freezr.aws.Account = factory

            old = Account.objects.get(pk=3).updated
            response = self.client.post(reverse('account-refresh', args=[3]))
            log.debug("response=%r factory=%r factory.mates=%r "
                      "factory.mate.calls=%r",
                      response, factory, factory.mates, factory.mate.calls)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(factory.mates), 1)
            self.assertEqual(len(factory.mate.calls), 8)
            self.assertNotEqual(Account.objects.get(pk=3).updated, old)

        finally:
            freezr.aws.Account = old_account
