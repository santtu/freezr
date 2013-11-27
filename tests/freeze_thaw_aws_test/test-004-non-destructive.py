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

    def test00FreezeEmptyProject(self):
        """003-10 Freeze an empty project"""

        return
        # It should be possible to freeze an empty, non-init
        # project. It doesn't make much of a sense, but it doesn't
        # make much of a sense to make a straightjacket requirement of
        # it either.
        project = self.project_vpc

        # validate directly from aws
        # ignore terminated, they can be from previous tests
        states = [i.state
                  for i in self.ec2.get_only_instances()
                  if i.state not in ('terminated', 'shutting-down')]

        self.log.debug("states: %r", states)

        self.assertTrue(all([s == 'running' for s in states]))
        self.assertEqual(len(states), 6)

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
            finally:
                self.until_project_in_state(project, ('frozen', 'running'))
                r = self.client.post(project + "thaw/")
                self.assertCode(r, 200)

                self.until_project_in_state(project, ('running',))

                # XXX there's timing problems here
                # XXX should really disable project updates while it
                # is transitioning --> test case for it
