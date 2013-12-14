import unittest
import logging
from freezr.core.filter import Filter, ParseException

log = logging.getLogger('freezr.tests.test_filter')


class TestFilter(unittest.TestCase):

    # These should fail, e.g. produce an exception
    FAIL = (
        '$bad',                 # invalid chars
        'bnarf = bnarf',        # literals not valid lhs values
        'foo und zing',         # invalid structure
        'region[bad]',          # only tag[indice]
        'tag[with space]',      # keys can have spaces, but not in literals
        'tag[one] == bad',      # invalid op
        'tag[one] <> bad',      # invalid op
        'tag[one] > bad',       # invalid op, maybe in future
        'tag[one] < bad',       # invalid op, maybe in future
        'region and',           # premature end of input
        '(region',              # ditto
        '(region and (',        # ditto
        '(region (region and region))',  # invalid parenthesis
        'region = (region or region)',  # invalid rhs
        '',                     # empty input
        )

    # These should succeed, and give the expected result (true or
    # false) given the environment defined below.

    SUCCESS = (
        # true/false literals
        ('true', True),
        ('false', False),

        # Basic value tests
        ('region', True),
        ('region = moon', False),
        ('region = us-east-1', True),
        ('region ~ "^u.*"', True),
        ('region ~ "[^0-9]$"', False),
        ('region !~ "[^0-9]$"', True),
        ('storage = ebs', True),
        ('storage != ebs', False),
        ('storage = instance', False),

        # Tag tests
        ('tag[class]', True),
        ('tag[class] = test', True),
        ('tag[class] != test', False),
        ('tag[class] = other', False),
        ('tag[class] != other', True),
        ('tag[unexistent]', False),
        ('tag[unexistent] = ""', True),
        ('tag[unexistent] = other', False),
        ('tag[unexistent] != other', True),

        # And/or/not logic tests
        ('false or false', False),
        ('true or false', True),
        ('false or true', True),
        ('true or true', True),

        ('false and false', False),
        ('true and false', False),
        ('false and true', False),
        ('true and true', True),

        ('tag[t] or tag[t]', True),
        ('tag[t] and tag[t]', True),
        ('tag[t] or tag[f]', True),
        ('tag[t] and tag[f]', False),
        ('tag[f] or tag[f]', False),
        ('tag[f] and tag[f]', False),
        ('not tag[f]', True),
        ('not tag[t]', False),
        ('not tag[f] or tag[f]', True),
        ('not ((tag[f] or tag[f] or tag[f] or tag[t]) and tag[f])', True),

        # Note that rhs can contain variables and tags too, so test
        # those too
        ('region = region', True),
        ('region = instance', False),
        ('tag[class] = tag[class]', True),
        ('tag[lit3] = storage', True),
        ('tag[lit2] != storage', True),
        ('storage = tag[lit3]', True),
        ('storage != tag[lit2]', True),
        ('tag[lit1] = tag[lit1]', True),
        )

    # Environment for the case above
    ENVIRONMENT = {
        'region': 'us-east-1',
        'instance': 'i-12345678',
        'type': 'm1.small',
        'storage': 'ebs',
        'tags': {
            'class': 'test',
            't': 'not empty',  # evaluates to true boolean
            'f': '',  # evaluates to false
            'lit1': 'something',
            'lit2': 'something',
            'lit3': 'ebs',
            },
        }

    def testFilterParseFail(self):
        succeeded = []

        for text in self.FAIL:
            try:
                f = Filter.parse(text)
                succeeded.append((text, f.format()))
            except ParseException:
                pass

        msg = ("Some failure cases succeeded in parsing:\n\n{0}"
               .format("\n".join(["\t{0:<20} => {1}"
                                  .format(*t) for t in succeeded])))

        self.assertEqual(len(succeeded), 0, msg)

    def testFilterParseSuccess(self):
        failed = []

        for case in self.SUCCESS:
            text = case[0]
            try:
                Filter.parse(text)
            except ParseException as ex:
                failed.append((text, str(ex)))

        msg = ("Some success cases failed in parsing:\n\n{0}"
               .format("\n".join(["\t{0:<20} => {1}".format(t[0], t[1])
                                  for t in failed])))

        self.assertEqual(len(failed), 0, msg)

    def testFilterEvaluationSuccess(self):
        failed = []

        for case in self.SUCCESS:
            text, expected = case
            # Don't care about exceptions here, testFilterParseSuccess
            # will produce nicer output on any failures of SUCCESS
            # elements.
            f = Filter.parse(text)
            log.debug("{0!r} parsed as {1!r}".format(text, f.format()))
            result = f.evaluate(self.ENVIRONMENT)
            log.debug("result is {0}".format(result))

            if result != expected:
                failed.append((text, expected, result))

        msg = ("Some success cases failed in parsing:\n\n{0}"
               .format("\n".join(["\t{0:<20} expected {1} got {2}"
                                  .format(*t) for t in failed])))

        self.assertEqual(len(failed), 0, msg)
