import unittest
import util

class ValidateAws(util.Mixin, unittest.TestCase):
    def test01AwsConnection(self):
        """000-01 Test we can access AWS account and there are instances"""
        self.assertTrue(len(self.ec2.get_only_instances()) > 0,
                        "AWS account does not contain any instances")
