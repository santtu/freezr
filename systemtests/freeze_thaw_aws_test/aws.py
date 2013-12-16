# aws.py - provide a fake cloud interface that will mimic some of
# "real" aws behavior.
#
# The implementation consists of `Mock` class which inherits from
# `freezr.backend.aws.AwsInterface` and replaces the normal `boto.ec2`
# connector with a custom one (`EC2Interface`) that mocks some of the
# ec2 interface.
#
# `EC2Interface` is synchronous but supports delayed operations like
# instance state transitions by having an internal list of pending
# operations which are checked on all public interface calls.
#
# This uses two global variables, `STATE` which is initialized to
# `AWS` instance based on `INSTANCES` global when first
# needed. `STATE` thereafter will store the persistent (fake) AWS
# state. If you need to reset the AWS environment during testing
# you'll have to set `STATE = None`, which will cause it to be
# re-initialized when it is needed next time.
#
# TODO: This should be part of the generic unit test framework, as it
# could be used there too (w/o the asynchronous faking, as unittest
# celery does all synchronously). This would allow exercising of
# `freezr.backend.aws.AwsInterface` during unit tests too.
#
# How to configure for testing:
#
# 1) Do nothing. The default INSTANCES list mimicks the CFN deployment
# (it is based on snapshot of actual CFN deployment, keeping all CFN
# meta keys intact).
#
# 2) Customize `INSTANCES` global variable **before** calls any AWS
# calls are made. (This will be used only during the setup of `STATE`
# and ignored afterwards.)
#
# 3) Assign `STATE` with your custom `AWS` state.

import logging
from copy import deepcopy
from Queue import PriorityQueue
from time import time
from freezr.backend.aws import AwsInterface

# Defaults that are used unless specified
DEFAULT_INSTANCE_TYPE = 't1.micro'
DEFAULT_ROOT_DEVICE_TYPE = 'ebs'
DEFAULT_REGION = 'us-east-1'
DEFAULT_STATE = 'pending'
DEFAULT_VPC_ID = None

# Default instance list -- this matches the CFN deployment
# configuration after deployment has completed (all instances are
# running, for example).
INSTANCES = [
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'tags': {'freezrtest': 'true',
              'Name': 'slave01',
              'service': 'public',
              'aws:cloudformation:logical-id': 'pubSlave01',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:'
               'us-east-1:319066637663:stack/freezr-test/'
               'df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'slave'},
     },
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'vpc_id': 'vpc-ec6d7b8e',
     'tags': {'freezrtest': 'true',
              'Name': 'master',
              'service': 'vpc',
              'aws:cloudformation:logical-id': 'vpcMaster',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:us-east-1:319066637663:stack/'
               'freezr-test/df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'ci'},
     },
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'tags': {'freezrtest': 'true',
              'Name': 'master',
              'service': 'public',
              'aws:cloudformation:logical-id': 'pubMaster',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:us-east-1:319066637663:stack/'
               'freezr-test/df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'ci'},
     },
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'vpc_id': 'vpc-ec6d7b8e',
     'tags': {'freezrtest': 'true',
              'Name': 'nat',
              'service': 'vpc',
              'aws:cloudformation:logical-id': 'vpcNatGateway',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:us-east-1:319066637663:stack/'
               'freezr-test/df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'infra'},
     },
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'vpc_id': 'vpc-ec6d7b8e',
     'tags': {'freezrtest': 'true',
              'Name': 'slave02',
              'service': 'vpc',
              'aws:cloudformation:logical-id': 'vpcSlave02',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:us-east-1:319066637663:stack/'
               'freezr-test/df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'slave'},
     },
    {'region': 'us-east-1',
     'state': 'running',
     'root_device_type': 'ebs',
     'instance_type': 't1.micro',
     'vpc_id': 'vpc-ec6d7b8e',
     'tags': {'freezrtest': 'true',
              'Name': 'slave01',
              'service': 'vpc',
              'aws:cloudformation:logical-id': 'vpcSlave01',
              'aws:cloudformation:stack-id':
              ('arn:aws:cloudformation:us-east-1:319066637663:stack/'
               'freezr-test/df094960-5b3c-11e3-ba4b-500150b34c7c'),
              'aws:cloudformation:stack-name': 'freezr-test',
              'role': 'slave'}
     },
    ]

STATE = None


# from http://stackoverflow.com/a/14620633/779129
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class AWS(object):
    """Abstraction of an AWS state. Typically this is fed `INSTANCES`
    on startup (via `Mock`) and this maintains information on state
    changes on those instances later, for example, terminated
    instances are marked terminated etc."""

    STABLE_INSTANCE_STATES = ('running', 'stopped', 'terminated')

    def __init__(self, instances=[]):
        """Initialize AWS state mockup from given list of
        `instances`. Each `instance` record in `instances` is a
        dictionary. See global `INSTANCES` for example on how to
        configure."""

        self.log = logging.getLogger('freezr.systemtests.aws.AWS')
        self.instances = {}
        self.count = 0
        self.ops = PriorityQueue()
        for instance in deepcopy(instances):
            self.add_instance(instance)

    def add_instance(self, data):
        """Adds a single instance data. This will set meaningful
        defaults on any missing fields (including instance id, which
        is autogenerated if missing). If the initial instance state is
        in a transitioning state it'll be scheduled for later update
        automatically."""

        self.count += 1

        instance = {
            'id': 'i-%06d' % (self.count,),
            'region': DEFAULT_REGION,
            'root_device_type': DEFAULT_ROOT_DEVICE_TYPE,
            'instance_type': DEFAULT_INSTANCE_TYPE,
            'state': DEFAULT_STATE,
            'vpc_id': DEFAULT_VPC_ID,
            'tags': {},
            }

        instance.update(data)
        self.instances[instance['id']] = instance

        if instance['state'] not in self.STABLE_INSTANCE_STATES:
            self.later(10, self.instance_state_proceed, instance)

        self.log.debug('Added instance: %r', instance)

    def later(self, secs, fn, *args, **kwargs):
        """Schedule an operation a minimum of `secs` later, calling
        `fn` with args `args` and kwargs `kwargs`."""
        when = time() + secs
        op = (when, lambda: fn(*args, **kwargs))
        self.ops.put(op)
        self.log.debug("Added later %.1fs: %r", secs, op)

    def tick(self):
        """'Tick' the AWS state by checking whether there are any
        pending operations (see `later`) that should be run before
        proceeding."""
        self.log.debug("tick (%d ops)", self.ops.qsize())
        while not self.ops.empty():
            when, call = self.ops.get_nowait()

            # not yet?
            if time() < when:
                self.log.debug("Task due in %.1fs, put it back",
                               when - time())
                self.ops.put((when, call))
                return

            self.log.debug("Running task due for %.1fs: %r",
                           when, call)

            call()

    def get_instances(self):
        """Return a list of instances. The returned list elements try
        to mimic the behavior of `boto.ec2.instances.Instance` to the
        extent needed by freezr."""
        self.tick()
        self.log.debug("get_instances: %d instances",
                       len(self.instances))
        return [AttrDict(instance) for instance in self.instances.values()]

    def terminate_instance(self, id):
        self.tick()
        self.log.debug("terminate_instance: %r", id)
        instance = self.instances[id]
        assert instance['state'] == 'running'
        instance['state'] = 'terminating'
        self.later(10, self.instance_state_proceed, instance)

    def stop_instance(self, id):
        self.tick()
        self.log.debug("stop_instance: %r", id)
        instance = self.instances[id]
        assert instance['state'] == 'running'
        instance['state'] = 'stopping'
        self.later(10, self.instance_state_proceed, instance)

    def start_instance(self, id):
        self.tick()
        self.log.debug("start_instance: %r", id)
        instance = self.instances[id]
        assert instance['state'] == 'stopped'
        instance['state'] = 'pending'
        self.later(10, self.instance_state_proceed, instance)

    # operations on instances
    def instance_state_proceed(self, instance):
        """Given an instance that is in a transitioning state, move it
        to the matching stable state (e.g. "pending" -> "running",
        "terminating" -> "terminated", "stopping" -> "stopped")."""

        self.log.debug("instance_state_proceed: instance %s, state %s",
                       instance['id'], instance['state'])

        state = instance['state']

        if state == 'pending':
            state = 'running'
        elif state == 'stopping':
            state = 'stopped'
        elif state == 'terminating':
            state = 'terminated'

        instance['state'] = state
        self.log.debug("instance_state_proceed: final state %s", state)


class EC2Interface(object):
    """This tries to mimic `boto.ec2.connection.EC2Connection` to the
    extent used by freezr."""

    def __init__(self, state, region):
        self.state = state
        self.region = region

    ########################################################################
    ## boto.ec2 interface mocks

    def get_only_instances(self, instance_ids=None):
        return [i for i in self.state.get_instances()
                if ((instance_ids is None or i.id in instance_ids) and
                    i.region == self.region)]

    # Note: {terminate,stop,start}_instances **do not** honor region
    # since we know that instance ids are unique over all regions in
    # our test setup. That is, you can kill instances in other regions
    # than the interface is nominally attached to...

    def terminate_instances(self, instance_ids=[]):
        for id in instance_ids:
            self.state.terminate_instance(id)

    def stop_instances(self, instance_ids=[]):
        for id in instance_ids:
            self.state.stop_instance(id)

    def start_instances(self, instance_ids=[]):
        for id in instance_ids:
            self.state.start_instance(id)


# Overlay of AWS interface class -- we override connect_ec2 and let
# the core class handle all of the "other" work.
class Mock(AwsInterface):
    """Use this as `settings.FREEZR_CLOUD_BACKEND` to **not** use a
    real AWS for calls, but the `EC2Interface` fake one instead. Apart
    from replacing the AWS connection with the `EC2Interface` mock
    this will not change `freezr.backend.aws.AwsInterface`
    behavior."""

    def __init__(self, access_key=None, secret_key=None):
        global STATE
        self.log = logging.getLogger('freezr.systemtests.aws.Mock')
        self.log.debug("access_key=%r", access_key)
        if not STATE:
            STATE = AWS(INSTANCES)

    def connect_ec2(self, region):
        self.log.debug("connect to region %r", region)
        return EC2Interface(STATE, region)
