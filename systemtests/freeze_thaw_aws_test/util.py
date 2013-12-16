import os
import requests
import logging
import json
import freezr.common.util as util
import time
import copy
from freezr.backend import get_backend
from functools import wraps

FILTER_KEYS = ('pick_filter', 'save_filter', 'terminate_filter')
DEFAULT_TIMEOUT = int(os.environ.get('DEFAULT_TEST_TIMEOUT', '300'))

requests.adapters.DEFAULT_RETRIES = 5
log = logging.getLogger('freezr.systemtests.util')


def only_real_aws(func):
    @wraps(func)
    def inner(self, *args, **kwargs):
        if self.real_aws:
            return func(self, *args, **kwargs)
    return inner


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
            assert path.startswith(self.base_url), \
                "{0} is not a valid path".format(path)
            return path

        return self.base_url + path

    def _encode(self, data):
        if data is None:
            return ''

        return json.dumps(data)

    def request(self, op_fn, path, data=None):
        url = self._url(path)

        self.log.debug("Request to %s with %s, data: %s",
                       url, op_fn, self._encode(data))

        r = op_fn(url,
                  headers={'Accept': 'application/json',
                           'Content-Type': 'application/json' },
                  data=self._encode(data))

        self.log.debug("Response status: %s", r.status_code)
        #self.log.debug("Response headers: %r", r.headers)

        if ((r.headers['content-type'] == 'application/json' and
             r.status_code not in (204,))):
            r.data = json.loads(r.text)

            # keep log_entries out of debug print in here, they are
            # way too verbose
            def prune(v):
                if isinstance(v, list):
                    return map(prune, v)
                if isinstance(v, dict) and 'log_entries' in v:
                    tmp = copy.copy(v)
                    del tmp['log_entries']
                    return tmp
                return v

            self.log.debug("Response JSON: %r", prune(r.data))
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

    ACCOUNT_DATA = {'name': 'AWS account'}
    DUMMY_ACCOUNT_DATA = {'name': 'Dummy account'}

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
        self.AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        self.real_aws = 'AWS_FAKE' not in os.environ
        self._ec2 = None
        self._cache = {}

    def setUp(self):
        self.client = Client()

    def assertCode(self, r, code):
        self.assertEqual(r.status_code, code)

    def filter_saver(self, project):
        class inner(object):
            def __init__(self, client, project, parent):
                self.client = client
                self.project = project
                self.parent = parent
                self.data = {}

            def __enter__(self):
                r = self.client.get(self.project)
                assert r.status_code == 200
                self.data = r.data
                return self

            def __exit__(self, type, value, traceback):
                try:
                    # No changes are possible while state is
                    # transitioning, so check and wait for that.
                    self.parent.until_project_in_state(self.project,
                                                       ('running', 'frozen'))
                    filters = {key: self.data[key] for key in FILTER_KEYS}
                    r = self.client.patch(self.project, filters)
                    self.parent.assertCode(r, 200)
                    self.parent.assertEqual(
                        {key: r.data[key] for key in FILTER_KEYS},
                        filters)
                except:
                    log.exception('oops')
                    if not type:
                        raise

            def __getitem__(self, key):
                return self.data[key]

        return inner(self.client, project, self)

    def resource_saver(self, url, data):
        """Save resourced `url`'s `data`. At __exit__ this will `put`
        the saved data."""

        class inner(object):
            def __init__(self, client, url, data, parent):
                self.client = client
                self.url = url
                self.data = data
                self.parent = parent
                # kludge
                self.is_project = 'pick_filter' in data
                log.debug('resource_saver: data=%r', data)

            def __enter__(self):
                return self

            def __exit__(self, type, value, traceback):
                if type:
                    log.debug('resource_saver: exception exit: %s',
                              value)

                try:
                    if self.is_project:
                        self.parent.until_project_in_state(
                            self.url,
                            ('running', 'frozen'))

                    log.debug('resource_saver: restoring %s: %r',
                              self.url, self.data)

                    r = self.client.put(self.url, self.data)
                    self.parent.assertCode(r, 200)
                except:
                    log.exception('oops')
                    if not type:
                        raise

            def __getitem__(self, key):
                return self.data[key]

        return inner(self.client, url, data, self)

    def match(self, data, pattern):
        keys = pattern.keys()
        values = set(pattern.values())

        for datum in data:
            if set([datum.get(field) for field in keys]) == values:
                self.log.debug("Match %r => %r",
                               pattern, self.cleanup(datum))
                return datum

        self.fail('Could not find datum matching %r from %r' %
                  (pattern, data))

    def timeout(self, secs=DEFAULT_TIMEOUT, fail=True):
        class inner(object):
            def __init__(self, until, fail):
                self.start = time.time()
                self.until = until
                self.fail = fail

            def __bool__(self):
                if fail and time.time() >= self.until:
                    assert False, "Timed out after %f seconds" % (
                        time.time() - self.start)

                return time.time() >= self.until

            def __nonzero__(self):
                return self.__bool__()

        return inner(time.time() + secs, fail)

    @property
    def ec2(self):
        if self._ec2:
            return self._ec2

        assert self.real_aws, \
            "This should not have been reached with fake AWS backend"

        self._ec2 = (get_backend(self.AWS_ACCESS_KEY_ID,
                                 self.AWS_SECRET_ACCESS_KEY)
                     .connect_ec2(self.AWS_REGION))

        # self._ec2 = boto.ec2.connect_to_region(
        #     self.AWS_REGION,
        #     aws_access_key_id=self.AWS_ACCESS_KEY_ID,
        #     aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY)

        self.assertIsNotNone(self._ec2)
        return self._ec2

    def _get(self, key, path, pattern):
        if key not in self._cache:
            class idstr(str):
                pass

            r = self.client.get(path)
            self.assertCode(r, 200)
            data = self.match(r.data, pattern)
            value = idstr("%s%s/" % (path, data['id']))
            setattr(value, 'id', data['id'])
            self._cache[key] = value

        return self._cache.get(key)

    def project_state(self, project):
        """Return `project`'s current state"""
        r = self.client.get(project)
        self.assertCode(r, 200)
        return r.data['state']

    def project_in_state(self, project, states):
        """Return true if `project` is in one of `states`"""
        return self.project_state(project) in states

    def until_project_in_state(self, project, states, timeout=None):
        """Wait until project is in one of `states`, with optionally
        specified timeout object of `timeout`. If `timeout` is not
        given, then this will use a default timeout.

        The default timeout is a failing one (self.timeout(fail=True))
        and will cause an exception if timeout is exceeded.

        If a non-failing timeout is given, this will return True if
        project is in given `states` at end of timeout, False
        otherwise."""
        timeout = timeout or self.timeout(fail=True)

        while not timeout and not self.project_in_state(project, states):
            time.sleep(2)

        return self.project_in_state(project, states)

    def until_project_not_in_state(self, project, states, timeout=None):
        """See `until_project_in_state`, this is otherwise identical
        except that it waits until project is **not** in one of the
        given states. (And returns True if project is **not** in given
        state at end of timeout.)"""
        timeout = timeout or self.timeout(fail=True)

        while not timeout and self.project_in_state(project, states):
            time.sleep(2)

        return not self.project_in_state(project, states)

    def instance_states(self):
        """Return instance states in the EC2 account."""
        states = [i.state
                  for i in self.ec2.get_only_instances()
                  if i.state not in ('terminated', 'shutting-down')]
        counts = {s: states.count(s) for s in set(states)}
        self.log.debug("instance states: %r", counts)
        return counts

    def until_instances_in_state(self, **states):
        """Wait until EC2 instances match the given states counts."""
        timeout = self.timeout()
        while not timeout:
            counts = self.instance_states()
            if counts == states:
                return

            time.sleep(2)

    @only_real_aws
    def until_instances_only_in_states(self, wanted_states):
        """Wait until instances are in the given list of states
        (regardless of number of instances, compare to
        until_instances_in_state.)"""
        wanted_states = set(wanted_states)
        timeout = self.timeout()
        while not timeout:
            states = set(self.instance_states().keys())

            # If states is a subset of wanted states, we have a
            # result.
            if states < wanted_states:
                return

            time.sleep(2)

    @only_real_aws
    def assertInstanceStates(self, **expected_counts):
        counts = self.instance_states()
        self.assertEqual(counts, expected_counts)

    def cleanup(self, data):
        """Remove entries from data meant for POST/PUT/PATCH
        operation. This removes read-only fields like `log_entries`
        which are useless to send."""
        tmp = copy.copy(data)
        for field in ('log_entries', 'instances',
                      'picked_instances', 'saved_instances',
                      'terminated_instances', 'skipped_instances'):
            if field in tmp:
                del tmp[field]
        return tmp

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
