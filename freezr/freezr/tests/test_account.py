from django import test
import logging
from freezr.models import Account, Domain, Project, Instance
from django.db.models import Q

log = logging.getLogger(__file__)

class TestAccount(test.TestCase):
    class MateMock(object):
        calls = []

        def refresh_region(self, account, region):
            self.calls.append((account, region))

    def setUp(self):
        self.domain = Domain(name="Test domain", domain=".test")
        self.domain.save()
        self.mate = TestAccount.MateMock()
        self.account = Account(domain=self.domain,
                               name="Test account",
                               access_key="1234",
                               secret_key="abcd",
                               mate=self.mate)
        self.account.save()

    def testAccountRefresh(self):
        # test account refresh calls the AWS mate object
        self.assertEqual(0, len(self.account.regions))

        self.account.refresh()
        self.assertEqual(0, len(self.mate.calls))

        Project(name="Test project", account=self.account,
                _regions="a,b,c,d,e,f").save()
        self.assertEqual(6, len(self.account.regions))

        self.account.refresh()
        self.assertEqual(6, len(self.mate.calls))
        self.assertTrue(all([c[0] == self.account for c in self.mate.calls]))
        self.assertEqual(set([u'a', u'b', u'c', u'd', u'e', u'f']), set([c[1] for c in self.mate.calls]))

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
