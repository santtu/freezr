# -*- coding: utf-8 -*-
import unittest
import time
from util import *

class NonDestructiveTests(Mixin, unittest.TestCase):
    """Only tests that are not destructive, e.g. are guaranteed to
    **not** terminate any instances, but that are not idempotent (see
    003). That is, the target environment may be left in arbitrary
    stopped/running state, but no instances should be terminated. That
    is, unless a test fails in which case all bets are off."""

    pass
