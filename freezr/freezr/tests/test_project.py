from django import test
import logging
from freezr.models import Account, Domain, Project, Instance
from django.db.models import Q
import freezr.tests.util as util

log = logging.getLogger(__file__)


class TestAccount(util.FreezrTestCaseMixin, test.TestCase):
    def setUp(self):
        self.domain = Domain(name="test", domain=".test")
        self.domain.save()
        self.account = Account(domain=self.domain, name="test",
                               access_key="1234",
                               secret_key="abcd")
        self.account.save()
        self.project = self.account.new_project(name="test")
        self.id = 10000
        self.instances = []

    def instance_filters(self, pick_filter, save_filter=None):
        class inner(object):
            def __init__(self, project, pick_filter, save_filter):
                self.project = project
                self.pick_filter = pick_filter
                self.save_filter = save_filter or pick_filter

            def __enter__(self):
                self.old_pick_filter = self.project.pick_filter
                self.old_save_filter = self.project.save_filter
                self.project.pick_filter = self.pick_filter
                self.project.save_filter = self.save_filter
                self.project.save()

            def __exit__(self, type, value, traceback):
                self.project.pick_filter = self.old_pick_filter
                self.project.save_filter = self.old_save_filter
                self.project.save()

        return inner(self.project, pick_filter, save_filter)


    def deleteInstances(self):
        for instance in self.instances:
            instance.delete()

        self.instances = []

    def createSet1(self):
        """create instance set 1 -- simple, three running instances,
        one nameless (but with empty Name tag) and two others named
        layer and hardy."""
        self.instances.extend([
                self.instance(tag_Name=''),
                self.instance(tag_Name='laurel'),
                self.instance(tag_Name='hardy')
                ])

    def createSet2(self):
        """instance set 2 -- 10 instances, where

        3 run in us-east-1: 1 stopped in us-east-1, 2 running tagged staging=yes, 1 stopped tagged devtest=yes
        2 stopped in us-west-2: tagged devtest=yes
        5 running in eu-west-1: tagged production=yes, 1 class=bastion, 2 class=db, 2 class=fe

        All are given names prefixed with the region descriptive name
        (nv - norther virginia, or - oregon, ir - ireland) and a
        running number.
        """
        sets = [
            {'region': 'us-east-1', 'state': 'running',
             'tag_staging': 'yes', 'tag_Name': 'nv01'},
            {'region': 'us-east-1', 'state': 'running',
             'tag_staging': 'yes', 'tag_Name': 'nv02'},
            {'region': 'us-east-1', 'state': 'stopped',
             'tag_devtest': 'yes', 'tag_Name': 'nv03'},

            {'region': 'us-west-2', 'state': 'stopped',
             'tag_devtest': 'yes', 'tag_Name': 'or01'},
            {'region': 'us-west-2', 'state': 'stopped',
             'tag_devtest': 'yes', 'tag_Name': 'or02'},

            {'region': 'eu-west-1', 'state': 'running',
             'tag_production': 'yes', 'tag_Name': 'ir01',
             'tag_class': 'bastion'},
            {'region': 'eu-west-1', 'state': 'running',
             'tag_production': 'yes', 'tag_Name': 'ir02',
             'tag_class': 'fe'},
            {'region': 'eu-west-1', 'state': 'running',
             'tag_production': 'yes', 'tag_Name': 'ir03',
             'tag_class': 'fe'},
            {'region': 'eu-west-1', 'state': 'running',
             'tag_production': 'yes', 'tag_Name': 'ir04',
             'tag_class': 'db'},
            {'region': 'eu-west-1', 'state': 'running',
             'tag_production': 'yes', 'tag_Name': 'ir05',
             'tag_class': 'db'},
            ]

        for data in sets:
            self.instances.append(self.instance(**data))

    def case_with_filters(self, *filters):
        for pick_filter, expected_count in filters:
            print(repr(pick_filter))
            with self.instance_filters(pick_filter):
                picked = self.project.picked_instances
                saved = self.project.saved_instances
                self.assertEqual(
                    expected_count, len(picked),
                    "Filter %r returned unexpected number of instances (wanted %d, got %d)" % (pick_filter, expected_count, len(picked)))
                self.assertEqual(set(picked), set(saved))

    def testNames1(self):
        # test different region filter patterns, verify correct
        # results
        self.createSet1()

        self.case_with_filters(
            ('', 0),
            ('region = region', 3),
            ('tag[Name]', 2),
            ('tag[Name] ~ l', 1),
            ('tag[Name] and tag[Name] !~ a', 0),
            ('not tag[Name]', 1))

    def testRegions1(self):
        self.createSet1()
        self.case_with_filters(
            ('region = us-east-1', 3),
            ('region ~ "^u.*east.*1$"', 3),
            ('region != us-west-1', 3),
            ('region != us-east-1', 0),
            ('region = us-west-1', 0),
            ('region = ap-northeast-1', 0))

    def testNames2(self):
        self.createSet2()
        self.case_with_filters(
            ('tag[Name]', 10),
            ('tag[Name] ~ "^n"', 3),
            ('tag[Name] ~ "^o"', 2),
            ('tag[Name] ~ "^i"', 5),
            ('tag[Name] ~ "02$" and region != us-west-2', 2),
            )

    def testMany2(self):
        self.createSet2()
        self.case_with_filters(
            ('tag[class] = bastion or tag[class] = fe', 3),
            ('tag[production]', 5),
            ('tag[production] or tag[devtest]', 8),
            ('tag[staging]', 2),
            )

    def testFreeze(self):
        aws = util.AwsMock()

        self.createSet2()
        with self.instance_filters('region = none'):
            self.project.freeze(aws=aws)

        self.assertEqual(aws.calls, [])

        # what is needed:
        #
        # attach project mate
        # count ops
        # compare expected with resulting instance state
        # restore project state back to running
        #

        self.fail('not yet implemented')

    def testThaw(self):
        # see freeze test case
        self.fail('not yet implemented')
