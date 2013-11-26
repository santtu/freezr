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

    def test03AccountRefresh(self):
        """003-03 Refresh an account via API call"""

        r = self.client.get(self.account)
        updated = r.data['updated']

        until = time.time() + 300

        while True:
            if time.time() > until:
                self.fail('Timed out waiting for account to update')

            r = self.client.post(self.account + "refresh/")
            self.assertCode(r, 202)

            time.sleep(2)

            r = self.client.get(self.account)
            if r.data['updated'] > updated:
                break

        self.log.debug("Account %s original update %s, now %s",
                       self.account, updated, r.data['updated'])

    def test04AccountUpdateWithoutSecret(self):
        """003-04 Account updates without secret key"""
        # It is possible to update account without the secret key, in
        # which case it is left untouched
        r = self.client.get(self.account)
        self.assertCode(r, 200)
        data = r.data
        self.assertFalse('secret_key' in data)

        r = self.client.put(self.account, data)
        self.assertCode(r, 200)

        r = self.client.patch(self.account, {})
        self.assertCode(r, 200)

    def test05InvalidAccountUpdate(self):
        """003-05 Try invalid account update operations"""
        data = self.client.get(self.account).data

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
        r = self.client.patch(self.account, {'domain': self.dummy_domain})
        self.assertCode(r, 200)
        self.assertEqual(r.data['domain'], data['domain'])

    def test06InvalidProjectUpdate(self):
        """003-06 Try invalid project update operations"""
        project = self.project_public
        data = self.client.get(project).data

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
        r = self.client.patch(project, {'account': self.dummy_account})
        self.assertCode(r, 200)
        self.assertEqual(r.data['account'], data['account'])
