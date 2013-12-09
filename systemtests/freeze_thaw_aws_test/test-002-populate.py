import unittest
import time
from util import *

class PopulateEnvironment(Mixin, unittest.TestCase):
    def test01PopulateDomain(self):
        """002-01 Populate test domain"""
        r = self.client.post("/domain/",
                             self.DOMAIN_DATA)

        self.assertCode(r, 201)

        r = self.client.post("/domain/",
                             self.DUMMY_DOMAIN_DATA)
        self.assertCode(r, 201)

    def test02PopulateAccount(self):
        """002-02 Populate test account"""
        r = self.client.post('/account/',
                             merge(self.ACCOUNT_DATA,
                                   domain=self.domain.id,
                                   access_key=self.AWS_ACCESS_KEY_ID,
                                   secret_key=self.AWS_SECRET_ACCESS_KEY))


        self.assertCode(r, 201)

        r = self.client.post('/account/',
                             merge(self.DUMMY_ACCOUNT_DATA,
                                   domain=self.dummy_domain.id,
                                   access_key='4298374984',
                                   secret_key='5432543534',
                                   active=False))

        self.assertCode(r, 201)

    def test03PopulateProjects(self):
        """002-03 Populate test projects"""
        r = self.client.post('/project/',
                             merge(self.PUBLIC_PROJECT_DATA,
                                   self.PUBLIC_PROJECT_VOLATILE,
                                   account=self.account.id,
                                   regions=[self.AWS_REGION]))
        self.assertCode(r, 201)

        r = self.client.post('/project/',
                             merge(self.VPC_PROJECT_DATA,
                                   self.VPC_PROJECT_VOLATILE,
                                   account=self.account.id,
                                   regions=[self.AWS_REGION]))

        self.assertCode(r, 201)

    def test04WaitProjectsRunning(self):
        """002-04 Wait until projects are running"""
        projects = [self.project_public, self.project_vpc]
        running = False
        timeout = self.timeout()

        self.log.debug("timeout=%r not=%r", timeout, not timeout)

        def running():
            r = self.client.get('/project/')
            self.assertCode(r, 200)
            return all([p['state'] == 'running' for p in r.data])

        while not timeout and not running():
            time.sleep(1)

        r = self.client.get('/project/')
        self.assertCode(r, 200)
        self.assertTrue(running())

        self.log.debug('Projects %r now running', projects)
