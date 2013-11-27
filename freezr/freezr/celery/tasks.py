from __future__ import absolute_import
from freezr.celery import app
from freezr.models import Account, Project, Instance
from django.utils import timezone
from datetime import timedelta
from celery.decorators import periodic_task
from celery.task.schedules import crontab
import logging
import freezr.aws
from celery import Celery


log = logging.getLogger('freezr.tasks')
# shutting-down is a transition, but from our point of view the
# instances is already gone when it starts that transition
STABLE_INSTANCE_STATES = ('running', 'stopped',
                            'terminated', 'shutting-down')
REFRESH_INSTANCE_INTERVAL = 5

# Just a debug task, get rid of it later.
@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

# The refresh task is scheduled to run every 10 minutes, but by
# default we'll update entries only older than 1 hour. This means that
# if an entry could not be updated (errors, failure in connection)
# then it'll be retried within 10 minutes.

@app.task()
@periodic_task(run_every=crontab(minute='*/10'))
def refresh(older_than=3600, regions=None):
    """Refreshes all accounts that have not been updated in
    `older_than` seconds."""

    limit = timezone.now() - timedelta(seconds=older_than)
    tasks = set()

    log.info('Refresh All: limit %d seconds', older_than)

    for account in Account.objects.filter(active=True).all():
        if account.updated is None or account.updated <= limit:
            tasks.add(refresh_account.delay(account.id))
        else:
            log.debug('Account %r update newer than %d seconds, '
                      'not refreshing',
                      account, older_than)

@app.task()
def refresh_account(pk, regions=None, older_than=None):
    """Refresh the given `pk` account, in given `regions`. If regions
    is None then all regions for the account will be checked. The
    `older_than` argument works like for refresh(), except by default
    it is not set."""

    account = Account.objects.get(id=pk)
    log.info('Refresh Account: %r, regions=%r', account, regions)

    if not account.active:
        return

    if older_than is None or older_than < 0:
        older_than = 0

    limit = timezone.now() - timedelta(seconds=older_than)
    if (older_than is not None and account.updated is not None and
        account.updated > limit):
        log.debug('Account %r update newer than %d seconds, not refreshing',
                  account, older_than)
        return

    # Ah well, probably should get a database transaction or something
    # like that here.
    account.refresh(regions=regions, aws=freezr.aws.AwsInterface(account))

    # See if any of the instances ended up in a "transitioning" state,
    # fire separate update tasks for them.
    for instance in account.instances.all():
        if instance.state not in STABLE_INSTANCE_STATES:
            log.debug('Refresh Account: Instance %s in transitioning '
                      'state "%s", scheduling refresh',
                      instance, instance.state)

            refresh_instance.apply_async([instance.id],
                                         countdown=REFRESH_INSTANCE_INTERVAL)

@app.task()
def freeze_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Freeze Project: %r', project)

    if not project.account.active:
        return

    project.freeze(aws=freezr.aws.AwsInterface(project.account))

@app.task()
def thaw_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Thaw Project: %r', project)

    if not project.account.active:
        return

    project.thaw(aws=freezr.aws.AwsInterface(project.account))

# Note: We don't have project.account.active check on instance checks,
# since refresh_instance cannot be directly triggered from outside, it
# is used in case we have already a need to do an instance refresh. So
# let's do it regardless of account active state.

@app.task()
def refresh_instance(pk):
    def get():
        try:
            return Instance.objects.get(id=pk)
        except Instance.DoesNotExist:
            return None

    instance = get()
    if not instance:
        log.info("Refresh instance: called on non-existent instance "
                 "pk=%r .. maybe it has already gone away otherwise?", pk)
        return

    instance_id = instance.instance_id
    log.info('Refresh instance: %r', instance)

    instance.refresh(aws=freezr.aws.AwsInterface(instance.account))

    instance = get()

    if not instance or instance.state in STABLE_INSTANCE_STATES:
        log.info('Refresh instance: Instance %s stabilized or gone away, '
                 'no need to reschedule', instance_id)
        return

    log.info('Refresh instance: instance %s still in '
             'a transitioning state "%s", rescheduling',
             instance, instance.state)

    refresh_instance.apply_async([pk], countdown=REFRESH_INSTANCE_INTERVAL)

@app.task()
def log_error(task_id):
    result = app.AsyncResult(task_id)
    result.get(propagate=False)
    log.error('Task failure: task %s, result %s, traceback:\n%s',
              task_id, result.result, result.traceback)
