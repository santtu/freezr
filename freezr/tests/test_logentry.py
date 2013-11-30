from django import test
import logging
from freezr.core.models import Account, Domain, Project, Instance, LogEntry
from freezr.api.exceptions import LoggedException, log_save
from django.db.models import Q

log = logging.getLogger(__file__)

class TestLogEntry(test.TestCase):
    def setUp(self):
        self.domain = Domain(name="test", domain=".test")
        self.domain.save()
        self.account = Account(domain=self.domain, name="test",
                               access_key="1234",
                               secret_key="abcd")
        self.account.save()
        self.project = self.account.new_project(name="test")
        self.project.save()
        self.instance = self.account.new_instance(instance_id='i-12345', type='m1.small', region='us-east-1', state='running')
        self.instance.save()

    def testPlainLogging(self):
        self.domain.log_entry('domain')
        self.assertEqual(1, LogEntry.objects.count())

        self.account.log_entry('account', type='exception')
        self.assertEqual(2, LogEntry.objects.count())

        self.project.log_entry('project', type='error')
        self.assertEqual(3, LogEntry.objects.count())

        self.instance.log_entry('instance', type='audit')
        self.assertEqual(4, LogEntry.objects.count())

        self.assertEqual(1, self.domain.log_entries.count())
        self.assertEqual(2, self.account.log_entries.count()) # instance goes here!
        self.assertEqual(1, self.project.log_entries.count())

        self.assertEqual('domain', self.domain.log_entries.all()[0].message)
        self.assertEqual('project', self.project.log_entries.all()[0].message)
        self.assertEqual(set(['account', 'instance']), set([l.message for l in self.account.log_entries.all()]))

        self.assertEqual(set(['info', 'exception', 'error', 'audit']),
                         set([l.type for l in LogEntry.objects.all()]))

    def testExceptionLogging(self):
        def throw():
            raise LoggedException(self.domain, 'problem')

        try:
            throw()
            self.fail('should not reach here')
        except LoggedException as ex:
            pass

        self.assertFalse(ex.saved)
        self.assertEqual(self.domain, ex.obj)
        self.assertEqual(0, LogEntry.objects.count())

        ex.save()

        self.assertTrue(ex.saved)
        self.assertEqual(1, LogEntry.objects.count())
        l = LogEntry.objects.all()[0]
        self.assertEqual(self.domain, l.domain)
        self.assertEqual('problem', l.message)
        self.assertEqual('exception', l.type)
