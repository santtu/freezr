from __future__ import absolute_import
import logging
from freezr.core.models import Account, Domain, Project, Instance
from django import test
from .util import AwsMockFactory, with_aws, AttrDict
import freezr.backend.tasks as tasks
from django.utils import timezone
from datetime import timedelta, datetime

log = logging.getLogger(__file__)

class instance_modifier(object):
    def __init__(self, **changes):
        self.changes = changes
        self.refreshes = 0

    def refresh_instance(self, instance):
        self.refreshes += 1

        log.debug("refresh_instance: instance=%r changes=%r",
                  instance, self.changes)

        for k, v in self.changes.iteritems():
            setattr(instance, k, v)
            log.debug("%s = %r", k, getattr(instance, k))

        instance.save()

class TestTasks(test.TestCase):
    def setUp(self):
        self.domain = Domain(name="test", domain=".test")
        self.domain.save()

        self.account = Account(domain=self.domain, name="test",
                               access_key="123", secret_key="456")
        self.account.save()

        self.project = Project(account=self.account, name="Test",
                               _regions="us-east-1")
        self.project.save()

        self.instance = self.account.new_instance(instance_id="i-123",
                                                  type="m1.small",
                                                  region="us-east-1",
                                                  state="running")
        self.instance.save()

    def case_transition(self, start, end, refresh_extra={}, **extras):
        obj = instance_modifier(state=end, **extras)

        with with_aws(AwsMockFactory(obj=obj)):
            self.instance.state = start
            self.instance.save()

            tasks.dispatch(tasks.refresh_instance.si(self.instance.id,
                                                     **refresh_extra)).get()

            self.instance = Instance.objects.get(pk=self.instance.id)
            self.assertEqual(self.instance.state, end)

        return obj

    def testInstanceRefreshWithTransition(self):
        # test refresh_instance where instance moves between states
        self.case_transition('stopping', 'stopped')
        self.case_transition('pending', 'running')

    def testInstanceRefreshWithAwsError(self):
        # test when AWS causes otherwise unexpected transition based
        # on an error case
        aws_instance = AttrDict(
            reason='fooled',
            state_reason={'code': 'Fooled.You',
                          'message': 'It is 1.4.'})

        def case(start, end, have_details, **kwargs):
            before_count = self.account.log_entries.count()
            self.case_transition(start, end, **kwargs)
            after_count = self.account.log_entries.count()

            self.assertEqual(after_count, before_count + 1,
                             'Log entries, expected %d, got %d' % (
                    before_count + 1, after_count))

            entry = self.account.log_entries.latest('time')
            self.assertEqual(entry.type, 'error')

            delta = timezone.now() - entry.time

            log.debug("%r - %r", entry.time, delta)

            self.assertLessEqual(delta.seconds, 1)
            self.assertEqual(len(entry.details if entry.details else '') != 0, have_details)
            self.assertFalse(entry.system_error)

        case('pending', 'stopped', False)
        case('pending', 'stopped', True, aws_instance=aws_instance)

        case('stopping', 'running', False)
        case('stopping', 'running', True, aws_instance=aws_instance)

    def account_refresh(self, timestamp=None):
        class updated_proxy(object):
            def __init__(self, parent):
                self.parent = parent
                self.id = self.parent.account.id

            @property
            def updated(self):
                account = Account.objects.get(pk=self.id)
                return account.updated

        class inner(object):
            def __init__(self, parent, timestamp):
                self.parent = parent
                self.timestamp = timestamp
                self.old = None
                self.id = self.parent.account.id

            def __enter__(self):
                account = Account.objects.get(pk=self.id)
                self.old = account.updated
                account.updated = self.timestamp
                account.save(update_fields=['updated'])
                return updated_proxy(self.parent)

            def __exit__(self, type, value, traceback):
                self.parent.account = Account.objects.get(pk=self.id)
                self.parent.account.updated = self.old
                self.parent.account.save(update_fields=['updated'])

        return inner(self, timestamp)

    def testAccountRefresh(self):
        # test that doing account refresh works, also that minimum
        # coercion and older_than work as expected

        def reset(timestamp=None):
            self.account.updated = timestamp
            self.account.save()

        factory = AwsMockFactory()
        with with_aws(factory):
            id = self.account.id

            # must refresh when updated = None
            with self.account_refresh() as proxy:
                tasks.dispatch(tasks.refresh_account.si(id, older_than=1000000)).get()
                self.assertIsNotNone(proxy.updated)
                self.assertIsNotNone(factory.aws)
                factory.assertUsed()
                factory.aws.assertCalled()

            factory.reset()

            # should NOT refresh
            with self.account_refresh(timezone.now()) as proxy:
                now = proxy.updated
                tasks.dispatch(tasks.refresh_account.si(id, older_than=1000000)).get()
                self.assertEqual(proxy.updated, now)
                factory.assertNotUsed()

            factory.reset()

            # should refresh
            with self.account_refresh(timezone.now() - timedelta(minutes=30)) as proxy:
                now = proxy.updated
                tasks.dispatch(tasks.refresh_account.si(id, older_than=(29*60))).get()
                self.assertNotEqual(proxy.updated, now)
                factory.assertUsed()
                factory.aws.assertCalled()

            factory.reset()

            # should not refresh, there's a minimum 5 second enforced
            # separation
            with self.account_refresh(timezone.now() - timedelta(seconds=2)) as proxy:
                now = proxy.updated
                tasks.dispatch(tasks.refresh_account.si(id, older_than=0)).get()
                self.assertEqual(proxy.updated, now)
                factory.assertNotUsed()

            # should refresh
            with self.account_refresh(timezone.now() - timedelta(seconds=5)) as proxy:
                now = proxy.updated
                tasks.dispatch(tasks.refresh_account.si(id, older_than=0)).get()
                self.assertNotEqual(proxy.updated, now)
                factory.assertUsed()
                factory.aws.assertCalled()

            factory.reset()

            # should refresh, grossly incorrect (in the future) timestamp
            with self.account_refresh(timezone.now() + timedelta(hours=10)) as proxy:
                now = proxy.updated
                tasks.dispatch(tasks.refresh_account.si(id, older_than=0)).get()
                self.assertNotEqual(proxy.updated, now)
                factory.assertUsed()
                factory.aws.assertCalled()
