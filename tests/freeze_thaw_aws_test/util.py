import os
import requests
import logging
import json
import boto.ec2
import freezr.util as util
import logging
import time

FILTER_KEYS = ('pick_filter', 'save_filter', 'terminate_filter')

requests.adapters.DEFAULT_RETRIES = 5
log = logging.getLogger('freeze_thaw_aws_test.util')

class Client(util.Logger):
    """Quick and dirty almost-like-real-django/rest-test-Client
    class."""
    def __init__(self):
        super(Client, self).__init__()

        host = os.environ.get('FREEZR_SERVER_HOST', 'localhost')
        port = int(os.environ.get('FREEZR_SERVER_PORT', '9000'))

        self.base_url = "http://{0}:{1}/api".format(host, port)
        self.s = requests.Session()

    def _url(self, path):
        if path[0] != '/':
            assert path.startswith(self.base_url), "{0} is not a valid path".format(path)
            return path

        return self.base_url + path

    def _encode(self, data):
        if data is None:
            return ''

        return json.dumps(data)

    def request(self, op_fn, path, data=None):
        url = self._url(path)

        self.log.debug("Request to %s with %s, data: %r",
                       url, op_fn, data)

        r = op_fn(url,
                  headers={'Accept': 'application/json',
                           'Content-Type': 'application/json' },
                  data=self._encode(data))

        self.log.debug("Response status: %s", r.status_code)
        self.log.debug("Response headers: %r", r.headers)

        if (r.headers['content-type'] == 'application/json' and
            r.status_code not in (204,)):

            self.log.debug("Response JSON: %s", r.text)
            r.data = json.loads(r.text)
        else:
            self.log.debug("Response text: %r", r.text)
            r.data = None

        return r

    def post(self, path, data={}):
        return self.request(self.s.post, path, data)

    def get(self, path):
        return self.request(self.s.get, path)

    def put(self, path, data={}):
        return self.request(self.s.put, path, data)

    def patch(self, path, data={}):
        return self.request(self.s.patch, path, data)

    def delete(self, path, data={}):
        return self.request(self.s.delete, path, data)

class Mixin(util.Logger):
    DOMAIN_DATA = {'domain': 'freezr.test.local',
                   'name': 'Freezr integration test domain'}

    # secondary dummy domain
    DUMMY_DOMAIN_DATA = {'domain': 'dummy.local',
                         'name': 'Dummay domain'}

    ACCOUNT_DATA = { 'name': 'AWS account'}
    DUMMY_ACCOUNT_DATA = { 'name': 'Dummy account' }

    # Keep identifying information in _DATA, and those that we might
    # modify during testing in _VOLATILE.
    PUBLIC_PROJECT_DATA = {'name': 'Project in public network'}
    PUBLIC_PROJECT_VOLATILE = {
        'pick_filter': 'tag[freezrtest] and tag[service] = public',
        'save_filter': 'tag[role] = ci',
        'terminate_filter': 'tag[role] = slave'}
    VPC_PROJECT_DATA = {'name': 'Project in VPC'}
    VPC_PROJECT_VOLATILE = {
        'pick_filter': 'tag[freezrtest] and tag[service] = "vpc"',
        'save_filter': 'tag[role] = ci',
        'terminate_filter': 'tag[role] = slave'}

    def __init__(self, *args, **kwargs):
        super(Mixin, self).__init__(*args, **kwargs)
        self.AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
        self.AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
        self.AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
        self._ec2 = None
        self._cache = {}

    def setUp(self):
        self.client = Client()

    def assertCode(self, r, code):
        self.assertEqual(r.status_code, code)

    def filter_saver(self, project):
        class inner(object):
            def __init__(self, client, project):
                self.client = client
                self.project = project
                self.data = {}

            def __enter__(self):
                r = self.client.get(self.project)
                assert r.status_code == 200
                self.data = r.data
                return self

            def __exit__(self, *args):
                filters = {key: self.data[key] for key in FILTER_KEYS}
                r = self.client.patch(self.project, filters)
                assert r.status_code == 200

            def __getitem__(self, key):
                return self.data[key]

        return inner(self.client, project)

    def resource_saver(self, data):
        """Save resource's `data`, which is assumed to contain a valid
        `url` for the resource. At __exit__ this will `put` the saved
        data."""

        class inner(object):
            def __init__(self, client, data):
                self.client = client
                self.data = data

            def __enter__(self):
                return self

            def __exit__(self, *args):
                try:
                    r = self.client.put(self.data['url'], self.data)
                except:
                    log.exception('oops')

                assert r.status_code == 200

            def __getitem__(self, key):
                return self.data[key]

        return inner(self.client, data)

    def match(self, data, pattern):
        keys = pattern.keys()
        values = set(pattern.values())

        for datum in data:
            if set([datum.get(field) for field in keys]) == values:
                self.log.debug("Match %r => %r", pattern, datum)
                return datum

        self.fail('Could not find datum matching %r from %r' % (
                pattern, data))

    def timeout(self, secs=300, fail=True):
        class inner(object):
            def __init__(self, until, fail):
                self.until = until
                self.fail = fail

            def __bool__(self):
                if fail and time.time() >= self.until:
                    assert False

                return time.time() >= self.until

        return inner(time.time() + secs, fail)

    @property
    def ec2(self):
        if self._ec2:
            return self._ec2

        self._ec2 = boto.ec2.connect_to_region(
            self.AWS_REGION,
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)

        self.assertIsNotNone(self._ec2)
        return self._ec2

    def _get(self, key, path, pattern):
        if key not in self._cache:
            r = self.client.get(path)
            self.assertCode(r, 200)
            self._cache[key] = self.match(r.data, pattern)['url']

        return self._cache.get(key)

    @property
    def domain(self):
        """Retrieve our test domain id -- have to use API, since if
        we're run repeatedly on the same server the id will
        increase."""
        return self._get('domain', '/domain/', self.DOMAIN_DATA)

    @property
    def dummy_domain(self):
        return self._get('dummy_domain', '/domain/', self.DUMMY_DOMAIN_DATA)

    @property
    def account(self):
        return self._get('account', '/account/', self.ACCOUNT_DATA)

    @property
    def dummy_account(self):
        return self._get('dummy_account', '/account/', self.DUMMY_ACCOUNT_DATA)

    @property
    def project_public(self):
        return self._get('project_public', '/project/',
                         self.PUBLIC_PROJECT_DATA)

    @property
    def project_vpc(self):
        return self._get('project_vpc', '/project/',
                         self.VPC_PROJECT_DATA)


def merge(*args, **kwargs):
    for arg in args:
        kwargs.update(arg)
    return kwargs
