from __future__ import absolute_import
import unittest
from . import util


class ValidateAws(util.Mixin, unittest.TestCase):
    def test01AwsConnection(self):
        """000-01 Test we can access AWS account and there are instances"""
        instances = [i for i in self.ec2.get_only_instances()
                     if i.state == 'running']
        self.assertTrue(len(instances) > 0,
                        "AWS account does not contain any running instances")
        self.assertTrue(len(instances) >= 6,
                        "AWS doesn't contain at least 6 "
                        "running instances: %s" % (instances,))

    def test02InstancesRunning(self):
        """000-02 Wait until all instances are running"""
        # .. or terminated, they might be leftovers from previous test
        self.until_instances_only_in_states(('running', 'terminated'))
