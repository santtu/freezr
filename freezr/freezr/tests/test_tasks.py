from __future__ import absolute_import
import logging
from freezr.models import Account, Domain, Project, Instance
from django import test
from .util import AwsMockFactory, with_aws, AttrDict
import freezr.celery.tasks as tasks
from django.utils import timezone

log = logging.getLogger(__file__)

class instance_modifier(object):
    def __init__(self, **changes):
        self.changes = changes

    def refresh_instance(self, instance):
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

        self.instance = self.account.new_instance(instance_id="i-123",
                                                  type="m1.small",
                                                  region="us-east-1",
                                                  state="running")
        self.instance.save()

    def case_transition(self, start, end, **extras):
        obj = instance_modifier(state=end, **extras)

        with with_aws(AwsMockFactory(obj=obj)):
            self.instance.state = start
            self.instance.save()

            tasks.dispatch(tasks.refresh_instance.si(self.instance.id)).get()

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
