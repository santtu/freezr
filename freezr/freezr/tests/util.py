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
