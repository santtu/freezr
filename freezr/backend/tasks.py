from __future__ import absolute_import
from .celery import app
from . import aws
from freezr.core.models import Account, Project, Instance
from django.utils import timezone
from datetime import timedelta
import logging
from celery import group, chain
from django.db.utils import OperationalError
from decorator import decorator

log = logging.getLogger('freezr.backend.tasks')
# shutting-down is a transition, but from our point of view the
# instances is already gone when it starts that transition
STABLE_INSTANCE_STATES = ('running', 'stopped',
                          'terminated', 'shutting-down')
REFRESH_INSTANCE_INTERVAL = 5
STABLE_PROJECT_STATES = ('error', 'running', 'frozen')
REFRESH_PROJECT_INTERVAL = 15
ACCOUNT_UPDATE_INTERVAL = 3600  # 1 hour


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
        log.debug('[%s] Retry on database error', args[0].request.id)
        #, exc_info=True)
        args[0].retry(exc=ex, countdown=15)  # more aggressive retry
                                             # schedule


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
@retry
def refresh(self, older_than=ACCOUNT_UPDATE_INTERVAL, regions=None):
    """Refreshes all accounts that have not been updated in
    `older_than` seconds."""

    limit = timezone.now() - timedelta(seconds=older_than)
    tasks = list()

    log.info('Refresh All: limit %d seconds', older_than)

    for account in Account.objects.filter(active=True).all():
        if account.updated is None or account.updated <= limit:
            tasks.append(refresh_account.si(account.id, older_than=older_than))
        else:
            log.debug('Account %r update newer than %d seconds, '
                      'not refreshing',
                      account, older_than)

    dispatch(group(*tasks))


@app.task(bind=True)
@retry
def refresh_account(self, pk, regions=None,
                    older_than=ACCOUNT_UPDATE_INTERVAL,
                    forced=False):
    """Refresh the given `pk` account, in given `regions`. If regions
    is None then all regions for the account will be checked. The
    `older_than` argument works like for refresh(), except by default
    it is not set."""

    try:
        account = Account.objects.get(id=pk)
    except Account.DoesNotExist:
        log.error('Refresh Account: Unexistent account %d', pk)
        return

    log.info('Refresh Account: %r (%s), updated=%r regions=%r, older_than=%r',
             account, "active" if account.active else "not active",
             account.updated, regions, older_than)

    if not account.active:
        return

    # Coerce minimum 5 second older_than
    older_than = max(5, older_than or 0)

    if account.updated is None:
        fresh = False
    else:
        delta = timezone.now() - account.updated
        fresh = not (
            # Not updated in the past, within older_than
            delta >= timedelta(seconds=older_than) or
            # Someone has a botched clock, timestamp is to the future,
            # force update
            delta < -timedelta(hours=1, seconds=older_than))

        log.debug("%s <=> %s --> delta=%s < %s = %s (forced %s)",
                  timezone.now(), account.updated, delta,
                  timedelta(seconds=older_than),
                  fresh, forced)

    if fresh and not forced:
        log.debug('Account %r update newer than %d seconds, not refreshing',
                  account, older_than)
        return

    # Ah well, probably should get a database transaction or something
    # like that here.
    account.refresh(regions=regions, aws=aws.AwsInterface(account))

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
def refresh_project(self, pk):
    try:
        project = Project.objects.get(id=pk)
    except Project.DoesNotExist:
        log.error('Refresh Project : Unexistent project %d', pk)

    project.refresh()

    # If project in transient state, schedule refresh.
    if project.state not in STABLE_PROJECT_STATES:
        dispatch(refresh_project.si(project.id),
                 countdown=REFRESH_PROJECT_INTERVAL)


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

    project.freeze(aws=aws.AwsInterface(project.account))

    # Schedule project refresh to watch instance states until all have
    # stabilised.
    if project.state == 'freezing':
        dispatch(refresh_project.si(project.id),
                 countdown=REFRESH_PROJECT_INTERVAL)


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

    project.thaw(aws=aws.AwsInterface(project.account))

    if project.state == 'thawing':
        dispatch(refresh_project.si(project.id),
                 countdown=REFRESH_PROJECT_INTERVAL)

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
    instance.refresh(aws=aws.AwsInterface(instance.account))

    # we want to use the old instance object if it is still valid
    if get():
        log.info("Refresh instance: after refresh, instance state is %s",
                 instance.state)

        log.debug("aws_instance=%r %r", getattr(instance, 'aws_instance'),
                  instance.aws_instance)

        # Yep, this is possible. Make an account log entry out of it.
        if (prev_state, instance.state) in (('pending', 'stopped'),
                                            ('stopping', 'running')):
            if instance.aws_instance:
                i = instance.aws_instance
                details = (
                    'Instance %s was starting, previous state %s and '
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


@app.task(bind=True)
def log_result(self, result, task=None):
    log.info('[%s] Result for "%s": %r', self.request.id, task or "unknown",
             result)
    # for n in dir(self):
    #     if n[0] != '_':
    #         log.debug("Task: %s = %r", n, getattr(self, n))


@app.task(bind=True)
@retry
def reissue_operations(self):
    for project in Project.objects.filter(state_actual='freezing'):
        dispatch(freeze_project.si(project.id))

    for project in Project.objects.filter(state_actual='thawing'):
        dispatch(thaw_project.si(project.id))
