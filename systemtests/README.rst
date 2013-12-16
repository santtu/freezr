==========================
 freezr integration tests
==========================

This directory is meant for system-level e.g. integration tests. At
least initially these are meant to be run by hand and not part of
automated test suite -- some of them use AWS, meaning they can incur
costs, and some require other services to be running and configured on
the system in a particular way.

  **IMPORTANT WARNING!** Integration tests *will provision AWS*
  resources which **cost money**. Running them is at **your** own
  expense!

Prerequisites
=============

* AWS credentials with permissions for `ec2:*` and `cloudformation:*`
  actions.

* `AWS CLI tool <http://aws.amazon.com/cli/>`_

* Trent Mick's `excellent command-line \`json\` tool <http://trentm.com/json/>`_.

Running integration tests
=========================

The easiest approach is to run `run-integration-test.sh` script::

  $ ./systemtests/run-integration-test.sh AWS-ACCESS-KEY-ID AWS-SECRET-ACCESS-KEY

You can also specify `KEY-NAME` and `REGION`, but these default to
empty (no key, you *can not* log in to instances) and
`us-east-1`. (You can also provide these values via environmental
variables AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and
AWS_DEFAULT_REGION.)

This will deploy `freezr-test` CloudFormation stack, run integration
tests against it and finally tear down the stack.

The more manual approach is to deploy the stack yourself, run tests
against it, and tear down the stack when you are done::

  $ cd systemtests
  $ export AWS_ACCESS_KEY_ID=<id>
  $ export AWS_SECRET_ACCESS_KEY=<secret>
  $ export AWS_DEFAULT_REGION=<region>
  $ ./deploy
  $ ./freeze-thaw-aws.sh
  $ ./deploy stop

If you want to run individual test sets directly, do::

  $ cd systemtests
  $ nosetests -x -v freeze_thaw_aws_test/...py

`run-integration-tests.sh` and `freeze-thaw-aws.sh` scripts will check
`USE_EXISTING_FREEZR` and `KEEP_FAILED_FREEZR` environment variables,
and if they are non-empty will either not deploy a new freezr test
environment or will not deprovision one in case of failure. For
example, if you want to repeat integration test until something fails,
do::

  $ export KEEP_FAILED_FREEZR=1
  $ while ./run-integration-tests.sh; do; done

and when you want to re-test using the same environment, do:

  $ export USE_EXISTING_FREEZR=1 SKIP_DESTRUCTIVE_TESTS=1
  $ while ./run-integration-tests.sh; do; done

**Note:** Some of the integration tests are destructive -- **you
cannot** run the whole suite without a full cloudformation stack
redeployment after running them. If you want to run integration tests
repeatedly you **must** also set `SKIP_DESTRUCTIVE_TESTS`.


Running integration tests without AWS
=====================================

It is possible to run the integration tests without an actual AWS
account. To do this, run:

  $ ./systemtests/run-fake-integration-test.sh

This will be almost like the real integration test **except the AWS
connection and state** are mocked. This test will not provision
CloudFormation stack. Of course, it cannot be guaranteed to 100% match
the real AWS environment, but apart from the actual `boto.ec2`
connection it will exercise same code paths as the real integration
test.
