import unittest
import util

class ResetEnvironment(util.Mixin, unittest.TestCase):
    def test01RemoveDomains(self):
        """001-01 Remove freezr resources from the system"""
        # note
        r = self.client.get('/domain/')
        self.assertCode(r, 200)

        self.log.debug('Got domains: %r', [d['id'] for d in r.data])

        for d in r.data:
            self.log.debug('Deleting domain %s', d['id'])
            r2 = self.client.delete(d['url'])
            self.assertCode(r2, 204)
