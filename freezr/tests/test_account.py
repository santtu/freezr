from __future__ import absolute_import
from django import test
import logging
import time
from freezr.core.models import Account, Domain, Project, Instance
from django.db.models import Q
from .util import AwsMock, FreezrTestCaseMixin

log = logging.getLogger(__file__)

class TestAccount(FreezrTestCaseMixin, test.TestCase):
    def setUp(self):
        self.domain = Domain(name="Test domain", domain=".test")
        self.domain.save()
        self.aws = AwsMock()
        self.account = Account(domain=self.domain,
                               name="Test account",
                               access_key="1234",
                               secret_key="abcd")
        self.account.save()

    def testAccountRefresh(self):
        # test account refresh calls the AWS interface object
        self.assertEqual(0, len(self.account.regions))
        self.assertIsNone(self.account.updated)

        old = self.account.updated

        # If there are no regions to update then there should be no
        # calls to aws interface, and the update timestamp should not
        # change from previous value.

        self.account.refresh(aws=self.aws)
        self.assertEqual(0, len(self.aws.calls))
        self.assertIsNone(self.account.updated)

        old = self.account.updated

        Project(name="Test project", account=self.account,
                _regions="a,b,c,d,e,f").save()
        self.assertEqual(6, len(self.account.regions))

        time.sleep(0.01) # make sure some time passes, we're comparing timestamps
        self.account.refresh(aws=self.aws)
        self.assertEqual(6, len(self.aws.calls))
        self.assertTrue(all([c[1] == self.account for c in self.aws.calls]))
        self.assertEqual(set([u'a', u'b', u'c', u'd', u'e', u'f']), set([c[2] for c in self.aws.calls]))
        self.assertNotEqual(old, self.account.updated)

        Project(name="Test project 2", account=self.account, _regions="").save()
        print(self.account.regions)
        self.assertEqual(6, len(self.account.regions))

        Project(name="Test project 3", account=self.account, _regions="a,k,l").save()
        self.assertEqual(8, len(self.account.regions))
        self.assertEqual(3, self.account.projects.count())

    def testAccountNewInstance(self):
        # test instance creation via account instance
        self.account.new_instance(instance_id="123", type="small",
                                  region="a", store="a", state="running").save()
        self.assertEqual(1, self.account.instances.count())
        i = self.account.instances.all()[0]
        self.assertEqual(self.account, i.account)
        self.assertEqual("123", i.instance_id)
        self.assertEqual("small", i.type)
        self.assertEqual("a", i.region)
        self.assertEqual("a", i.store)
        self.assertEqual("running", i.state)

    def testAccountInstances(self):
        # test multiple instances already in db show up correctly in
        # account
        for i in range(9):
            Instance(account=self.account, instance_id=str(i),
                     type="small", region="a",
                     store="a", state="running" if (i % 2) == 0 else "stopped").save()

        self.assertEqual(9, self.account.instances.count())
        self.assertEqual(5, self.account.instances.filter(state="running").count())
        self.assertEqual(4, self.account.instances.filter(~Q(state="running")).count())

    def testAccountProjectState(self):
        # test that account moves projects from init state to running
        # when the project matches instances

        p = self.account.new_project(name='test',
                                     _regions='a',
                                     pick_filter='tag[Name] = target')
        p.save()
        project_id = p.id

        def assertState(state):
            self.assertEqual(Project.objects.get(pk=project_id).state,
                             state)

        # First verify that it is in the expected state at beginning.
        assertState('init')

        # Refresh should not change that
        self.account.refresh(aws=self.aws)
        assertState('init')

        # Not even when there's (non-matching) instance.
        self.instance(region='a')
        self.account.refresh(aws=self.aws)
        assertState('init')

        # But when there's one ...
        i = self.instance(region='a', tag_Name='target')
        self.account.refresh(aws=self.aws)
        assertState('running')

        # even if it later goes away
        i.delete()
        self.account.refresh(aws=self.aws)
        assertState('running')


    def testRegionsDisappearing(self):
        # test case when region is removed from project on account,
        # removing that region from the complete list -- instances on
        # non-reachable regions should be removed
        p = self.account.new_project(name="test", _regions="a,b")
        p.save()

        for id, region in (('i-0001', 'a'), ('i-0002', 'b')):
            i = self.account.new_instance(instance_id=id, region=region,
                                          type='m1.small', state='running')
            i.save()

        self.assertEqual(self.account.instances.count(), 2)
        self.assertEqual(self.account.regions, ['a', 'b'])

        self.account.refresh(aws=self.aws)
        self.assertEqual(self.account.instances.count(), 2)

        p.regions = ['a']
        p.save()

        self.assertEqual(self.account.regions, ['a'])

        self.account.refresh(aws=self.aws)
        self.assertEqual(self.account.instances.count(), 1)
