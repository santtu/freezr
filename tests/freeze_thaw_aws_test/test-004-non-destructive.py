# -*- coding: utf-8 -*-
import unittest
import time
from util import *

class NonDestructiveTests(Mixin, unittest.TestCase):
    """Only tests that are not destructive, e.g. are guaranteed to
    **not** terminate any instances, but that are not idempotent (see
    003). That is, the target environment may be left in arbitrary
    stopped/running state, but no instances should be terminated. That
    is, unless there's bug or a test fails in which case all bets are
    off."""

    def instance_states(self):
        states = [i.state
                  for i in self.ec2.get_only_instances()
                  if i.state not in ('terminated', 'shutting-down')]
        counts = {s: states.count(s) for s in set(states)}
        self.log.debug("instance states: %r", counts)
        return counts

    def until_instances_in_state(self, **states):
        timeout = self.timeout()
        while not timeout:
            counts = self.instance_states()
            if counts == states:
                return

            time.sleep(2)

    def test01FreezeEmptyProjectAndRefreeze(self):
        """004-01 Freeze an empty project, attempt re-freeze"""

        # It should be possible to freeze an empty, non-init
        # project. It doesn't make much of a sense, but it doesn't
        # make much of a sense to make a straightjacket requirement of
        # it either.
        project = self.project_vpc

        # validate directly from aws
        # ignore terminated, they can be from previous tests
        counts = self.instance_states()
        self.assertEqual(counts, {'running': 6})

        with self.filter_saver(project) as data:
            self.assertEqual(data['state'], 'running')
            try:
                r = self.client.patch(project, {'pick_filter':'false'})
                self.assertCode(r, 200)
                self.assertEqual(r.data['picked_instances'], [])
                self.assertEqual(r.data['terminated_instances'], [])
                self.assertEqual(r.data['saved_instances'], [])
                self.assertEqual(r.data['skipped_instances'], [])

                r = self.client.post(project + "freeze/")
                self.assertCode(r, 202)

                self.until_project_in_state(project, ('frozen',))

                # validate that all instances are still running and
                # none has been terminated or stopped or in any other
                # non-running state
                counts = self.instance_states()
                self.assertEqual(counts, {'running': 6})

                # try to freeze again, expect a failure
                r = self.client.post(project + "freeze/")
                self.assertCode(r, 409)
                self.assertEqual(self.project_state(project), 'frozen')
            finally:
                # running here too in case assert picks up before
                # project is frozen
                self.until_project_in_state(project, ('frozen', 'running'))

                if self.project_state(project) == 'frozen':
                    r = self.client.post(project + "thaw/")
                    self.assertCode(r, 202)

                self.until_project_in_state(project, ('running',))

    def test02FreezeFullProject(self):
        """004-02 Freeze all instances in a project"""

        project = self.project_public

        # validate directly from aws
        # ignore terminated, they can be from previous tests
        counts = self.instance_states()
        self.assertEqual(counts, {'running': 6})

        with self.filter_saver(project) as data:
            self.assertEqual(data['state'], 'running')
            try:
                r = self.client.patch(project, {'save_filter': 'true'})
                self.assertCode(r, 200)
                self.assertEqual(len(r.data['picked_instances']), 2)
                self.assertEqual(r.data['terminated_instances'], [])
                self.assertEqual(len(r.data['saved_instances']), 2)
                self.assertEqual(r.data['skipped_instances'], [])

                r = self.client.post(project + "freeze/")
                self.assertCode(r, 202)

                self.until_project_in_state(project, ('frozen',))

                # validate that all instances are still running and
                # none has been terminated or stopped or in any other
                # non-running state
                self.until_instances_in_state(running=4, stopped=2)
            finally:
                # running here too in case assert picks up before
                # project is frozen
                self.until_project_in_state(project, ('frozen', 'running'))

                if self.project_state(project) == 'frozen':
                    r = self.client.post(project + "thaw/")
                    self.assertCode(r, 202)

                self.until_project_in_state(project, ('running',))
                self.until_instances_in_state(running=6)

    # TODO 03: Freeze only some, skip some. Freeze and thaw.

    # TODO 04: What happens if we remove region -- do we delete
    # instances in those regions (unit test)

    # TODO 05: Verify that unexpected state changes are logged (unit test)
