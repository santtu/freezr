from __future__ import absolute_import
from .celery import app
from .models import Account, Project
from django.utils import timezone
from datetime import timedelta
from celery.decorators import periodic_task
from celery.task.schedules import crontab
import logging
#from freezr.aws import AwsInterface
import freezr.aws

log = logging.getLogger('freezr.tasks')

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

    for account in Account.objects.all():
        if account.updated is None or account.updated <= limit:
            tasks.add(refresh_account.delay(account.id))
        else:
            log.debug('Account %r update newer than %d seconds, not refreshing',
                      account, older_than)

@app.task()
def refresh_account(pk, regions=None, older_than=None):
    """Refresh the given `pk` account, in given `regions`. If regions
    is None then all regions for the account will be checked. The
    `older_than` argument works like for refresh(), except by default
    it is not set."""

    account = Account.objects.get(id=pk)
    log.info('Refresh Account: %r, regions=%r', account, regions)

    if older_than is None or older_than < 0:
        older_than = 0

    limit = timezone.now() - timedelta(seconds=older_than)
    if older_than is not None and account.updated is not None and account.updated > limit:
        log.debug('Account %r update newer than %d seconds, not refreshing',
                  account, older_than)
        return

    # Ah well, probably should get a database transaction or something
    # like that here.
    account.refresh(regions=regions, aws=freezr.aws.AwsInterface(account))

@app.task()
def freeze_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Freeze Project: %r', project)
    project.freeze(aws=freezr.aws.AwsInterface(project.account))

@app.task()
def thaw_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Thaw Project: %r', project)
    project.thaw(aws=freezr.aws.AwsInterface(project.account))
