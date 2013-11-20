from __future__ import absolute_import
from .celery import app
from .models import Account
from datetime import datetime, timedelta
import logging

log = logging.getLogger('freezr.tasks')

# Just a debug task, get rid of it later.
@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.task()
def refresh(older_than=3600, regions=None):
    """Refreshes all accounts that have not been updated in
    `older_than` seconds."""

    limit = datetime.now() - timedelta(seconds=older_than)
    tasks = set()

    log.info('Refresh All: limit %d seconds', older_than)

    for account in Account.objects.all():
        if account.updated is None or account.updated <= limit:
            tasks.add(refresh_account.delay(account.id))

@app.task()
def refresh_account(pk, regions=None):
    """Refresh the given `pk` account, in given `regions`. If regions
    is None then all regions for the account will be checked."""

    account = Account.objects.get(id=pk)
    log.info('Refresh Account: %r, regions=%r', account, regions)

    # Ah well, probably should get a database transaction or something
    # like that here.
    account.refresh(regions)

@app.task()
def freeze_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Freeze Project: %r', project)
    project.freeze()

@app.task()
def thaw_project(pk):
    project = Project.objects.get(id=pk)
    log.info('Thaw Project: %r', project)
    project.thaw()
