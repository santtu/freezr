from __future__ import absolute_import
from freezr.celery import app
from freezr.models import Account, Project, Instance
from django.utils import timezone
from datetime import timedelta
from celery.decorators import periodic_task
from celery.task.schedules import crontab
import logging
import freezr.aws
from celery import Celery, group, chain
from celery.result import GroupResult
from celery.exceptions import Retry
from functools import wraps
from django.db.utils import OperationalError
from decorator import decorator

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

@decorator
def retry(func, *args, **kwargs):
    """Decorator to automatically retry the task when certain
    exceptions (database rollbacks, locks etc.) are encountered, as we
    have a very strong expectation that these will work if retried.

    Note to self: Be careful, you don't want to retry things caused by
    program errors, they won't go away on repeats."""
    log.debug("wrapper call for %s: args=%r kwargs=%r", func, args, kwargs)
    try:
        return func(*args, **kwargs)
    except OperationalError as ex:
        log.debug('[%s] Retry on database error', args[0].request.id, exc_info=True)
        args[0].retry(exc=ex, countdown=15) # more aggressive retry schedule

# def retry(func):
#     """Decorator to automatically retry the task when certain
#     exceptions (database rollbacks, locks etc.) are encountered, as we
#     have a very strong expectation that these will work if retried.

#     Note to self: Be careful, you don't want to retry things caused by
#     program errors, they won't go away on repeats."""
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         log.debug("wrapper call for %s: args=%r kwargs=%r", func, args, kwargs)
#         try:
#             return func(*args, **kwargs)
#         except OperationalError as ex:
#             log.debug('Retry on database error', exc_info=True)
#             raise Retry(str(ex))

#     return wrapper

def dispatch(task, **kwargs):
    """Dispatches the given task with default error and result
    handlers. Returns the async object."""
    final_task = chain(task, log_result.s(task=repr(task)))
    async = final_task.apply_async(link_error=log_error.s(),
                                   **kwargs)
    log.info('[%s] Dispatched "%r"', async, task)
    return async

# The refresh task is scheduled to run every 10 minutes, but by
# default we'll update entries only older than 1 hour. This means that
# if an entry could not be updated (errors, failure in connection)
# then it'll be retried within 10 minutes.

@app.task(bind=True)
@periodic_task(run_every=crontab(minute='*/10'))
@retry
def refresh(self, older_than=3600, regions=None):
    """Refreshes all accounts that have not been updated in
    `older_than` seconds."""

    limit = timezone.now() - timedelta(seconds=older_than)
    tasks = set()

    log.info('Refresh All: limit %d seconds', older_than)

    for account in Account.objects.filter(active=True).all():
        if account.updated is None or account.updated <= limit:
            tasks.add(refresh_account.si(account.id))
        else:
            log.debug('Account %r update newer than %d seconds, '
                      'not refreshing',
                      account, older_than)

    dispatch(group(*tasks))


@app.task(bind=True)
@retry
def refresh_account(self, pk, regions=None, older_than=None):
    """Refresh the given `pk` account, in given `regions`. If regions
    is None then all regions for the account will be checked. The
    `older_than` argument works like for refresh(), except by default
    it is not set."""

    try:
        account = Account.objects.get(id=pk)
    except Account.DoesNotExist:
        log.error('Refresh Account: Unexistent account %d', pk)
        return

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

            dispatch(refresh_instance.si(instance.id),
                     countdown=REFRESH_INSTANCE_INTERVAL)

@app.task(bind=True)
@retry
def freeze_project(self, pk):
    try:
        project = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        log.error('Freeze Project : Unexistent project %d', pk)

    log.info('Freeze Project: %r', project)

    if not project.account.active or project.state != 'freezing':
        return

    project.freeze(aws=freezr.aws.AwsInterface(project.account))

@app.task(bind=True)
@retry
def thaw_project(self, pk):
    try:
        project = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        log.error('Thaw Project : Unexistent project %d', pk)

    log.info('Thaw Project: %r', project)

    if not project.account.active or project.state != 'thawing':
        return

    project.thaw(aws=freezr.aws.AwsInterface(project.account))

# Note: We don't have project.account.active check on instance checks,
# since refresh_instance cannot be directly triggered from outside, it
# is used in case we have already a need to do an instance refresh. So
# let's do it regardless of account active state.

@app.task(bind=True)
@retry
def refresh_instance(self, pk):
    def get():
        try:
            return Instance.objects.get(id=pk)
        except Instance.DoesNotExist:
            log.error('Refresh Instance: Unexistent instance %d', pk)
            return

    instance = get()
    if not instance:
        log.info("Refresh instance: called on non-existent instance "
                 "pk=%r .. maybe it has already gone away otherwise?", pk)
        return

    instance_id = instance.instance_id
    log.info('Refresh instance: %r, previous known state %s',
             instance, instance.state)

    prev_state = instance.state
    instance.refresh(aws=freezr.aws.AwsInterface(instance.account))

    # we want to use the old instance object if it is still valid
    if get():
        log.info("Refresh instance: after refresh, instance state is %s",
                 instance.state)

        log.debug("aws_instance=%r %r", getattr(instance, 'aws_instance'), instance.aws_instance)

        # Yep, this is possible. Make an account log entry out of it.
        if (prev_state, instance.state) in (('pending', 'stopped'),
                                            ('stopping', 'running')):
            if instance.aws_instance:
                i = instance.aws_instance
                details=('Instance %s was starting, previous state %s and '
                         'current state is %s.\n\n'
                         'Server reason: %s\n'
                         'State reason code: %s\n'
                         'State reason message: %s\n' % (
                        instance.instance_id,
                        prev_state, instance.state,
                        i.reason,
                        i.state_reason['code'],
                        i.state_reason['message']))
            else:
                details = None

            instance.account.log_entry(
                'Problem starting instance %s' % (instance.instance_id,),
                details=details,
                type='error')

        if instance.state in STABLE_INSTANCE_STATES:
            log.info('Refresh instance: Instance %s stabilized, '
                     'no need to reschedule', instance_id)
            return
    else:
        log.info('Refresh instance: Instance %s gone away, '
                 'no need to reschedule', instance_id)
        return

    log.info('Refresh instance: instance %s still in '
             'a transitioning state "%s", rescheduling',
             instance, instance.state)

    dispatch(refresh_instance.si(pk),
             countdown=REFRESH_INSTANCE_INTERVAL)


@app.task()
def log_error(task_id):
    result = app.AsyncResult(task_id)
    result.get(propagate=False)
    log.error('Task failure: task %s, result %s, traceback:\n%s',
              task_id, result.result, result.traceback)

# from inspect import getargspec
# log.info("++++++++ retry = {0!r}".format(retry))
# log.info("++++++++ refresh_instance = {0!r}".format(refresh_instance))
# log.info("======== getargspec(retry) = {0!r}".format(getargspec(retry)))
# log.info("======== getargspec(refresh_instance) = {0!r}".format(getargspec(refresh_instance)))

@app.task(bind=True)
def log_result(self, result, task=None):
    log.info('[%s] Result for "%s": %r', self.request.id, task or "unknown", result)
    # for n in dir(self):
    #     if n[0] != '_':
    #         log.debug("Task: %s = %r", n, getattr(self, n))
