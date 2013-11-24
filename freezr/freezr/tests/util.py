class MateMock(object):
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.calls = []
        self.fail = False
        self.result = (0, 0, 0)

    def refresh_region(self, account, region):
        if self.fail:
            raise Exception('intentional failure')

        self.calls.append((account, region))
        return self.result

class MateMockFactory(object):
    def __init__(self):
        self.mates = []
        self.mate = None

    def __call__(self, *args, **kwargs):
        self.mate = MateMock(*args, **kwargs)
        self.mates.append(self.mate)
        return self.mate

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
