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
            r2 = self.client.delete('/domain/%s/' % (d['id'],))
            self.assertCode(r2, 204)

    def test02WebWorking(self):
        """001-02 Test that the actual non-api entry point works"""
        r = self.client.get(self.client.host_url + "/",
                            accept="text/html")
        self.assertCode(r, 200)
