# -*- coding: utf-8 -*-
import unittest
import time
from util import *

class IdempotentTests(Mixin, unittest.TestCase):
    """Only tests that are not destructive and actually would work
    regardless of the order they are run. That is, these tests must
    upon success restore the previous state back.

    Note that these are not required to restore on failure --- the
    integration tests are always run on -x nosetests flag (terminate
    on first failure).

    OTOH, it is nice feature to the values if possible, since that
    allowes easier re-run of these test cases..."""

    def caseFilterManipulation(self, project, orig_counts, test_set):
        def assertCounts(data, counts):
            self.assertEqual(len(data['picked_instances']), counts[0])
            self.assertEqual(len(data['saved_instances']), counts[1])
            self.assertEqual(len(data['terminated_instances']), counts[2])
            self.assertEqual(len(data['skipped_instances']), counts[3])

        r = self.client.get(project)
        self.assertCode(r, 200)

        assertCounts(r.data, orig_counts)

        with self.filter_saver(project) as orig:
            for filters, counts in test_set:
                self.log.debug('Filters: %r', filters)
                self.log.debug('Counts: %r', counts)

                data = {}
                for key, value in zip(FILTER_KEYS, filters):
                    if value is True:
                        data[key] = orig[key]
                    elif value is not None:
                        data[key] = value

                self.log.debug("Updating project %s with %r", project, data)

                r = self.client.patch(project, data)
                self.assertCode(r, 200)

                assertCounts(r.data, counts)

        r = self.client.get(project)
        self.assertCode(r, 200)
        assertCounts(r.data, orig_counts)

    def test01PublicProjectFilterManipulation(self):
        """003-01 Manipulate public project filters"""
        self.caseFilterManipulation(self.project_public,
                                    (2, 1, 1, 0),
                                    (
                (('false', None, None), (0, 0, 0, 0)),
                ((True, 'false', 'false'), (2, 0, 0, 2)),
                ((None, 'true', 'true'), (2, 2, 0, 0)),
                ))

    def test02VpcProjectFilterManipulation(self):
        """003-02 Manipulate vpc project filters"""
        self.caseFilterManipulation(self.project_vpc,
                                    (4, 1, 2, 1),
                                    (
                (('false', None, None), (0, 0, 0, 0)),
                ((True, 'false', 'false'), (4, 0, 0, 4)),
                ((None, 'true', 'true'), (4, 4, 0, 0)),
                ))

    def test03AccountUpdateWithoutSecret(self):
        """003-03 Account updates without secret key"""
        # It is possible to update account without the secret key, in
        # which case it is left untouched
        r = self.client.get(self.account)
        self.assertCode(r, 200)
        self.assertFalse('secret_key' in r.data)
        data = self.cleanup(r.data)

        r = self.client.put(self.account, data)
        self.assertCode(r, 200)

        r = self.client.patch(self.account, {})
        self.assertCode(r, 200)

    def test04InvalidAccountUpdate(self):
        """003-04 Try invalid account update operations"""
        data = self.cleanup(self.client.get(self.account).data)

        # Post on existing object
        r = self.client.post(self.account, data)
        self.assertCode(r, 405)

        # Incomplete update
        del data['access_key']
        r = self.client.put(self.account, data)
        self.assertCode(r, 400)

        # Invalid values
        r = self.client.patch(self.account, {'access_key': None})
        self.assertCode(r, 400)

        r = self.client.patch(self.account, {'access_key': ''})
        self.assertCode(r, 400)

        # The domain update on immutable field should just be ignored,
        # turning the request into no-op.
        r = self.client.patch(self.account, {'domain': self.dummy_domain.id})
        self.assertCode(r, 200)
        self.assertEqual(r.data['domain'], data['domain'])

    def test05InvalidProjectUpdate(self):
        """003-05 Try invalid project update operations"""
        project = self.project_public
        data = self.cleanup(self.client.get(project).data)

        # Post on existing object
        r = self.client.post(project, data)
        self.assertCode(r, 405)

        # Incomplete update
        del data['name']
        r = self.client.put(project, data)
        self.assertCode(r, 400)

        # Invalid values
        r = self.client.patch(project, {'name': None})
        self.assertCode(r, 400)

        r = self.client.patch(project, {'name': ''})
        self.assertCode(r, 400)

        # The account update on immutable field should just be
        # ignored, turning the request into no-op.
        r = self.client.patch(project, {'account': self.dummy_account.id})
        self.assertCode(r, 200)
        self.assertEqual(r.data['account'], data['account'])

    def test06AccountRefresh(self):
        """003-06 Refresh an account via API call"""

        r = self.client.get(self.account)
        updated = r.data['updated']

        timeout = self.timeout()

        while not timeout:
            r = self.client.post(self.account + "refresh/")
            self.assertCode(r, 202)

            time.sleep(2)

            r = self.client.get(self.account)
            if r.data['updated'] > updated:
                break

        self.log.debug("Account %s original update %s, now %s",
                       self.account, updated, r.data['updated'])

    def test07DisabledAccountRefresh(self):
        """003-07 Refresh a disabled account via API call"""

        r = self.client.get(self.account)
        self.assertCode(r, 200)
        self.assertTrue(r.data['active'])
        updated = r.data['updated']

        with self.resource_saver(self.account, self.cleanup(r.data)):
            r = self.client.patch(self.account, {'active': False})
            self.assertCode(r, 200)
            self.assertFalse(r.data['active'])
            r = self.client.get(self.account)
            self.log.debug("r.data=%r", r.data)
            self.assertFalse(r.data['active'])

            r = self.client.post(self.account + "refresh/")
            self.assertCode(r, 403)
            self.assertTrue('error' in r.data)

        r = self.client.get(self.account)
        self.assertTrue(r.data['active'])

    def test08DisabledAccountProjectFreeze(self):
        """003-08 Freeze project on disabled account"""
        r = self.client.get(self.project_public)
        self.assertEqual(r.data['state'], 'running')

        r = self.client.get(self.account)
        self.assertCode(r, 200)

        with self.resource_saver(self.account, self.cleanup(r.data)):
            r = self.client.patch(self.account, {'active': False})
            self.assertCode(r, 200)
            self.assertFalse(r.data['active'])
            r = self.client.get(self.account)
            self.assertFalse(r.data['active'])

            r = self.client.post(self.project_public + "freeze/")
            self.assertCode(r, 403)
            self.assertTrue('error' in r.data)

        r = self.client.get(self.account)
        self.assertTrue(r.data['active'])

    # Note: Cannot do similar test for thaw here since it requires
    # freezing first. See 004 tests.

    def test09ThawOnRunningProject(self):
        """003-09 Thaw a non-frozen project"""
        r = self.client.get(self.project_public)
        self.assertCode(r, 200)
        self.assertEqual(r.data['state'], 'running')

        r = self.client.post(self.project_public + "thaw/")
        self.assertCode(r, 409)
        self.assertTrue('error' in r.data)

    # Note: Similar argument for freeze on frozen project here. See 004.

    def test10RemoveRegion(self):
        """003-10 Remove region from account's projects"""
        # Those instances should disappear really quickly.
        old_regions = []

        r = self.client.get(self.account)
        self.assertCode(r, 200)
        orig_instances = r.data['instances']
        self.assertEqual(len(orig_instances), 6)

        r = self.client.get("/project/")
        self.assertCode(r, 200)

        try:
            for p in r.data:
                url = "/project/%s/" % (p['id'],)
                old_regions.append((url, p['regions']))
                r = self.client.patch(url, {'regions': []})
                self.assertCode(r, 200)

            r = self.client.get(self.account)
            self.assertCode(r, 200)
            self.assertEqual(r.data['regions'], [])

            # 5 minute timeout is ok, the account has just been refreshed
            # so it won't be otherwise updated during this time
            timeout = self.timeout()

            while not timeout:
                r = self.client.get(self.account)
                self.assertCode(r, 200)

                self.log.debug("account instances: %r", r.data['instances'])
                if len(r.data['instances']) == 0:
                    break

                time.sleep(2)
        finally:
            for url, regions in old_regions:
                r = self.client.patch(url, {'regions': regions})
                self.assertCode(r, 200)
                self.assertEqual(r.data['regions'], regions)

            while not timeout:
                r = self.client.get(self.account)
                self.assertCode(r, 200)

                self.log.debug("account instances: %r", r.data['instances'])
                if len(r.data['instances']) == 6:
                    break

                time.sleep(2)

            self.assertEqual(set(r.data['instances']), set(orig_instances))
