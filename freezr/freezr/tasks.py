from __future__ import absolute_import
from .celery import app
from .models import Account
from datetime import datetime, timedelta

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))

@app.task()
def refresh(older_than=3600, regions=None):
    """Refreshes all accounts that have not been updated in
    `older_than` seconds."""

    limit = datetime.now() - timedelta(seconds=older_than)
    tasks = set()

    print('Refresh All: limit {0} seconds'.format(older_than))

    for account in Account.objects.all():
        if account.updated is None or account.updated <= limit:
            tasks.add(refresh_account.delay(account.id))

@app.task()
def refresh_account(pk, regions=None):
    account = Account.objects.get(id=pk)
    print('Refresh Account: {0!r}'.format(account))
    if regions:
        account.refresh(regions)
    else:
        account.refresh()

@app.task()
def freeze_project(pk):
    project = Project.objects.get(id=pk)
    print('Freeze Project: {0!r}'.format(project))
    project.freeze()

@app.task()
def thaw_project(pk):
    project = Project.objects.get(id=pk)
    print('Thaw Project: {0!r}'.format(project))
    project.thaw()
