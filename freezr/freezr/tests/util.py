import logging

log = logging.getLogger('freezr.tests.util')

class AwsMock(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []
        self.fail = False
        self.result = (0, 0, 0)

        log.debug('AwsMock.__init__: args=%r kwargs=%r', args, kwargs)

    def refresh_region(self, account, region):
        log.debug('AwsMock.refresh_region: account=%r region=%r',
                  account, region)

        if self.fail:
            raise Exception('intentional failure')

        self.calls.append((account, region))
        return self.result

class AwsMockFactory(object):
    def __init__(self):
        self.aws_list = []
        self.aws = None

    def __call__(self, *args, **kwargs):
        self.aws = AwsMock(*args, **kwargs)
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
