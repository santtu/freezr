from django import test
import logging
from freezr.core.models import Account, Domain, Project, Instance
from django.db.models import Q
import freezr.tests.util as util

log = logging.getLogger(__file__)

def arg(lst, n):
    return [e[n] for e in lst]

def ids(lst):
    return [i.instance_id for i in lst]

class TestAccount(util.FreezrTestCaseMixin, test.TestCase):
    def setUp(self):
        self.domain = Domain(name="test", domain=".test")
        self.domain.save()
        self.account = Account(domain=self.domain, name="test",
                               access_key="1234",
                               secret_key="abcd")
        self.account.save()
        self.project = self.account.new_project(name="test", state='running')
        self.project.save()
        self.id = 10000
        self.instances = []

    def instance_filters(self,
                         pick_filter,
                         save_filter=None,
                         terminate_filter=None):
        class inner(object):
            def __init__(self, project,
                         pick_filter, save_filter, terminate_filter):
                self.project = project
                self.pick_filter = pick_filter
                self.save_filter = save_filter or ''
                self.terminate_filter = terminate_filter or ''

            def __enter__(self):
                self.old_pick_filter = self.project.pick_filter
                self.old_save_filter = self.project.save_filter
                self.old_terminate_filter = self.project.terminate_filter
                self.project.pick_filter = self.pick_filter
                self.project.save_filter = self.save_filter
                self.project.terminate_filter = self.terminate_filter
                self.project.save()
                log.debug("project %s pick %r save %r terminate %r",
                          self.project,
                          self.project.pick_filter,
                          self.project.save_filter,
                          self.project.terminate_filter)

            def __exit__(self, type, value, traceback):
                self.project.pick_filter = self.old_pick_filter
                self.project.save_filter = self.old_save_filter
                self.project.terminate_filter = self.old_terminate_filter
                self.project.save()

        return inner(self.project, pick_filter, save_filter, terminate_filter)


    def deleteInstances(self):
        """Delete all instances directly from DB so far created within
        this test case."""
        for instance in self.instances:
            instance.delete()

        self.instances = []

    def createSet1(self):
        """Create instance set 1 -- simple, three running instances,
        one nameless (but with empty Name tag) and two others named
        layer and hardy."""
        self.instances.extend([
                self.instance(tag_Name=''),
                self.instance(tag_Name='laurel'),
                self.instance(tag_Name='hardy')
                ])

    def createSet2(self, override={}):
        """Create instance set 2 -- 10 instances, where

        3 run in us-east-1: 1 stopped in us-east-1, 2 running tagged
        staging=yes, 1 stopped tagged devtest=yes

        2 stopped in us-west-2: tagged devtest=yes

        5 running in eu-west-1: tagged production=yes, 1
        class=bastion, 2 class=db, 2 class=fe

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
            data = {k: v for k, v in data.iteritems()}
            data.update(override)
            self.instances.append(self.instance(**data))

    def case_with_filters(self, *filters):
        for pick, save, terminate in filters:
            # pick, save and terminate are tuples of (filter,
            # expected)

            pick = pick or ('', 0)
            save = save or ('', 0)
            terminate = terminate or ('', 0)

            print("pick={0!r} save={1!r} terminate={2!r}".
                  format(pick, save, terminate))

            with self.instance_filters(pick[0], save[0], terminate[0]):
                picked = self.project.picked_instances
                saved = self.project.saved_instances
                terminated = self.project.terminated_instances
                skipped = self.project.skipped_instances

                for what, got, expected in (
                    ('picked', len(picked), pick[1]),
                    ('saved', len(saved), save[1]),
                    ('terminated', len(terminated), terminate[1]),
                    ('skipped', len(skipped), len(picked) - len(saved) - len(terminated))):
                    self.assertEqual(
                        expected, got,
                        "Filters pick=%r, save=%r, terminate=%r returned "
                        "unexpected number "
                        "of instances for %r filter: %d instead "
                        "of expected %d):\npicked = %r\nsaved = %r\nterminated = %r\nskipped = %r" % (
                            pick[0], save[0], terminate[0],
                            what, got, expected,
                            picked, saved, terminated, skipped))

    def testNames1(self):
        # test different region filter patterns, verify correct
        # results
        self.createSet1()

        self.case_with_filters(
            (('', 0), None, None),
            (('region = region', 3), None, None),
            (('tag[Name]', 2), None, None),
            (('tag[Name] ~ l', 1), None, None),
            (('tag[Name] and tag[Name] !~ a', 0), None, None),
            (('not tag[Name]', 1), None, None))

    def testRegions1(self):
        self.createSet1()
        self.case_with_filters(
            (('region = us-east-1', 3), None, None),
            (('region ~ "^u.*east.*1$"', 3), None, None),
            (('region != us-west-1', 3), None, None),
            (('region != us-east-1', 0), None, None),
            (('region = us-west-1', 0), None, None),
            (('region = ap-northeast-1', 0), None, None))

    def testNames2(self):
        self.createSet2()
        self.case_with_filters(
            (('tag[Name]', 10), None, None),
            (('tag[Name] ~ "^n"', 3), None, None),
            (('tag[Name] ~ "^o"', 2), None, None),
            (('tag[Name] ~ "^i"', 5), None, None),
            (('tag[Name] ~ "02$" and region != us-west-2', 2), None, None),
            )

    def testMany2(self):
        self.createSet2()
        self.case_with_filters(
            (('tag[class] = bastion or tag[class] = fe', 3), None, None),
            (('tag[production]', 5), None, None),
            (('tag[production] or tag[devtest]', 8), None, None),
            (('tag[staging]', 2), None, None),
            )

    def testExclusions2(self):
        # test also save and terminate filters, try to construct
        # overlaps to see they are not honored
        self.createSet2()
        self.case_with_filters(
            (('true', 10), ('false', 0), ('false', 0)),
            (('true', 10), ('true', 10), ('false', 0)),
            # any instance saved is automatically excluded from
            # termination, no matter what termination filter says
            (('true', 10), ('true', 10), ('true', 0)),
            (('true', 10), ('false', 0), ('true', 10)),
            (('true', 10), ('tag[staging] or tag[devtest]', 5), ('tag[staging] or tag[devtest] or true', 5)),
            )

    def testFreeze(self):
        self.createSet2()
        aws = util.AwsMock()

        def reset():
            self.project.state = 'running'
            self.project.save()
            aws.reset()

        # ------

        self.assertState('running')
        # With nothing to save or terminate, no calls.
        with self.instance_filters('region = none'):
            self.project.freeze(aws=aws)

        self.assertState('frozen')
        self.assertEqual(aws.calls, [])

        # With only saved instances, there are two staging instances.
        reset()
        self.assertState('running')
        with self.instance_filters('tag[staging]', 'true'):
            self.project.freeze(aws=aws)

        self.assertState('frozen')
        self.assertEqual(len(aws.calls), 2)
        self.assertEqualSet(ids(arg(aws.calls, 1)), ('i-000001', 'i-000002'))

        # Verify we can save all.
        reset()
        self.assertState('running')
        with self.instance_filters('true', 'true'):
            self.project.freeze(aws=aws)

        self.assertState('frozen')
        self.assertEqual(len(aws.calls), 10)
        self.assertEqualSet(ids(arg(aws.calls, 1)), [i.instance_id for i in Instance.objects.all()])

        # Save staging, terminate devtest, ignore production.
        reset()
        self.assertState('running')
        with self.instance_filters('true', 'tag[staging]', 'tag[devtest]'):
            self.project.freeze(aws=aws)

        self.assertState('frozen')
        self.assertEqual(len(aws.calls), 5)

        self.assertEqual({t[1].instance_id: t[0] for t in aws.calls},
                         {u'i-000001': 'freeze_instance',
                          u'i-000002': 'freeze_instance',
                          u'i-000003': 'terminate_instance',
                          u'i-000004': 'terminate_instance',
                          u'i-000005': 'terminate_instance'})

    def assertState(self, state):
        self.assertEqual(Project.objects.get(pk=self.project.id).state,
                         state)

    def testThaw(self):
        self.createSet2(override={'state': 'stopped'})
        aws = util.AwsMock()

        def reset():
            self.project.state = 'frozen'
            self.project.save()
            aws.reset()

        # ------

        reset()
        self.assertState('frozen')

        # With nothing to thaw, no calls
        with self.instance_filters('region = none'):
            self.project.thaw(aws=aws)

        self.assertState('running')
        self.assertEqual(aws.calls, [])

        reset()
        self.assertState('frozen')
        with self.instance_filters('tag[staging]', 'true'):
            self.project.thaw(aws=aws)

        self.assertState('running')
        self.assertEqual(len(aws.calls), 2)
        self.assertEqualSet(ids(arg(aws.calls, 1)), ('i-000001', 'i-000002'))

        # Verify we can save all.
        reset()
        with self.instance_filters('true', 'true'):
            self.project.thaw(aws=aws)

        self.assertState('running')
        self.assertEqual(len(aws.calls), 10)
        self.assertEqualSet(ids(arg(aws.calls, 1)), [i.instance_id for i in Instance.objects.all()])

        # Save staging, terminate devtest, ignore production.
        reset()
        with self.instance_filters('true', 'tag[staging] or tag[devtest]'):
            self.project.thaw(aws=aws)

        self.assertState('running')
        self.assertEqual(len(aws.calls), 5)

        self.assertEqual({t[1].instance_id: t[0] for t in aws.calls},
                         {u'i-000001': 'thaw_instance',
                          u'i-000002': 'thaw_instance',
                          u'i-000003': 'thaw_instance',
                          u'i-000004': 'thaw_instance',
                          u'i-000005': 'thaw_instance'})

    def testFreezeThaw(self):
        aws = util.AwsMock()
        self.assertState('running')
        self.project.freeze(aws)
        self.assertState('frozen')
        self.project.thaw(aws)
        self.assertState('running')

    def testRefreeze(self):
        # check that we can issue freeze on a project that has been
        # already marked for freezing
        aws = util.AwsMock()

        self.project.state = 'freezing'
        self.project.save()

        self.project.freeze(aws)
        self.assertEqual(self.project.state, 'frozen')

    def testRethaw(self):
        # same applies for thawing
        aws = util.AwsMock()

        self.project.state = 'thawing'
        self.project.save()

        self.project.thaw(aws)
        self.assertEqual(self.project.state, 'running')
