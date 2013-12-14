# -*- coding: utf-8 -*-
import unittest
from util import Mixin


class NonDestructiveTests(Mixin, unittest.TestCase):
    """Only tests that are not destructive, e.g. are guaranteed to
    **not** terminate any instances, but that are not idempotent (see
    003). That is, the target environment may be left in arbitrary
    stopped/running state, but no instances should be terminated. That
    is, unless there's bug or a test fails in which case all bets are
    off."""

    def assertFilterCounts(self, data, counts):
        for field, expected in zip(('picked_instances', 'saved_instances',
                                    'terminated_instances',
                                    'skipped_instances'),
                                   counts):
            count = len(data[field])
            self.log.debug("%s %d <=> %d", field, count, expected)
            self.assertEqual(count, expected,
                             'Filtered instance field "%s" value '
                             '%r has length %d, '
                             'expected %d instances' %
                             (field, data[field], count, expected))

    def test01FreezeEmptyProjectAndRefreeze(self):
        """004-01 Freeze an empty project, attempt re-freeze"""

        # It should be possible to freeze an empty, non-init
        # project. It doesn't make much of a sense, but it doesn't
        # make much of a sense to make a straightjacket requirement of
        # it either.
        project = self.project_vpc

        # validate directly from aws
        # ignore terminated, they can be from previous tests
        self.assertInstanceStates(running=6)

        with self.filter_saver(project) as data:
            self.assertEqual(data['state'], 'running')
            try:
                r = self.client.patch(project, {'pick_filter': 'false'})
                self.assertCode(r, 200)
                # self.assertEqual(r.data['picked_instances'], [])
                # self.assertEqual(r.data['terminated_instances'], [])
                # self.assertEqual(r.data['saved_instances'], [])
                # self.assertEqual(r.data['skipped_instances'], [])
                self.assertFilterCounts(r.data, (0, 0, 0, 0))

                self.freeze_project(project)

                self.until_project_in_state(project, ('frozen',))

                # validate that all instances are still running and
                # none has been terminated or stopped or in any other
                # non-running state
                self.assertInstanceStates(running=6)

                # try to freeze again, expect a failure
                r = self.client.post(project + "freeze/")
                self.assertCode(r, 409)
                self.assertEqual(self.project_state(project), 'frozen')
            finally:
                self.restore_project(project)

    def test02FreezeFullProject(self):
        """004-02 Freeze all instances in a project"""

        project = self.project_public

        # validate directly from aws
        # ignore terminated, they can be from previous tests
        self.assertInstanceStates(running=6)

        with self.filter_saver(project) as data:
            self.assertEqual(data['state'], 'running')
            try:
                r = self.client.patch(project, {'save_filter': 'true'})
                self.assertCode(r, 200)
                # self.assertEqual(len(r.data['picked_instances']), 2)
                # self.assertEqual(r.data['terminated_instances'], [])
                # self.assertEqual(len(r.data['saved_instances']), 2)
                # self.assertEqual(r.data['skipped_instances'], [])
                self.assertFilterCounts(r.data, (2, 2, 0, 0))

                self.freeze_project(project)
                self.until_project_in_state(project, ('frozen',))

                # All instances should be in their final state,
                # frozen, running or terminated at this
                # point. 'freezing' should not turn into 'frozen'
                # until the operation is complete.
                self.assertInstanceStates(running=4, stopped=2)

                # # validate that all instances are still running and
                # # none has been terminated or stopped or in any other
                # # non-running state
                # self.until_instances_in_state(running=4, stopped=2)
                # #self.assertInstanceStates(running=4, stopped=2) #tautology
            finally:
                self.restore_project(project)

    def restore_project(self, project):
        # running here too in case assert picks up before
        # project is frozen
        self.until_project_in_state(project, ('frozen', 'running'))

        if self.project_state(project) == 'frozen':
            self.thaw_project(project)

        self.until_project_in_state(project, ('running',))
        self.assertInstanceStates(running=6)
        #self.until_instances_in_state(running=6)

    def freeze_project(self, project):
        r = self.client.post(project + "freeze/")
        self.assertCode(r, 202)

    def thaw_project(self, project):
        r = self.client.post(project + "thaw/")
        self.assertCode(r, 202)

    def test03FreezePartialProject(self):
        """004-03 Freeze some instances in project"""
        project = self.project_vpc
        self.assertInstanceStates(running=6)
        with self.filter_saver(project) as data:
            self.assertEqual(data['state'], 'running')
            try:
                r = self.client.patch(project, {'terminate_filter': 'false'})
                self.assertCode(r, 200)
                self.assertFilterCounts(r.data, (4, 1, 0, 3))

                self.freeze_project(project)
                self.until_project_in_state(project, ('frozen',))
                self.assertInstanceStates(running=5, stopped=1)
                #self.until_instances_in_state(running=5, stopped=1)
            finally:
                self.restore_project(project)

    # TODO 04: What happens if we remove region -- do we delete
    # instances in those regions (unit test)
