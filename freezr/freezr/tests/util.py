import logging

log = logging.getLogger('freezr.tests.util')

class AwsMock(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []
        self.result = (0, 0, 0)

        log.debug('AwsMock.__init__: args=%r kwargs=%r', args, kwargs)

    def reset(self):
        self.calls = []

    def refresh_region(self, account, region):
        log.debug('AwsMock.refresh_region: account=%r region=%r',
                  account, region)

        self.calls.append(('refresh_region', account, region))
        return self.result

    def freeze_instance(self, instance):
        log.debug('AwsMock.freeze_instance: instance=%r', instance)
        self.calls.append(('freeze_instance', instance))

    def thaw_instance(self, instance):
        log.debug('AwsMock.thaw_instance: instance=%r', instance)
        self.calls.append(('thaw_instance', instance))

    def terminate_instance(self, instance):
        log.debug('AwsMock.terminate_instance: instance=%r', instance)
        self.calls.append(('terminate_instance', instance))

class AwsMockFactory(object):
    def __init__(self, cls=AwsMock, obj=None):
        self.aws_list = []
        self.aws = None
        self.cls = cls
        self.obj = obj

    def __call__(self, *args, **kwargs):
        if self.obj:
            return self.obj

        self.aws = self.cls(*args, **kwargs)
        self.aws_list.append(self.aws)
        return self.aws

class FreezrTestCaseMixin(object):
    _instance_id = 0

    def instance(self, account=None, **kwargs):
        """Easier instance creation -- will put sensible defaults,
        like unique id if not present etc. Tags are specified via
        giving either `tags` argument, or via tag_KEY=VALUE arguments
        (or both)."""
        account = account or self.account

        self._instance_id += 1

        kwargs.setdefault('instance_id', "i-%06d" % (self._instance_id,))
        kwargs.setdefault('type', 'm1.small')
        kwargs.setdefault('region', 'us-east-1')
        kwargs.setdefault('state', 'running')

        tags = kwargs.pop('tags', {})

        # extract all tags .. they are prefixed tag_
        for n in [n for n in kwargs.keys() if n.startswith('tag_')]:
            tags[n[4:]] = kwargs.pop(n)

        i = account.new_instance(**kwargs)
        i.save()

        for k, v in tags.iteritems():
            t = i.new_tag(key=k, value=v)
            t.save()

        return i

    def assertEqualSet(self, list1, list2):
        self.assertSetEqual(set(list1), set(list2))

def with_aws(aws):
    class inner(object):
        def __init__(self, aws):
            self.aws = aws
            self.old_aws = None

        def __enter__(self):
            import freezr.aws
            self.old_aws = freezr.aws.AwsInterface
            freezr.aws.AwsInterface = self.aws

        def __exit__(self, type, value, traceback):
            import freezr.aws
            freezr.aws.AwsInterface = self.old_aws

    return inner(aws)

# from http://stackoverflow.com/a/14620633/779129
class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
