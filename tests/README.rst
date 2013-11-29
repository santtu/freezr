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

Running tests
=============

The easiest approach is to run `run-integration-test.sh` script::

  $ ./tests/run-integration-test.sh AWS-ACCESS-KEY-ID AWS-SECRET-ACCESS-KEY

You can also specify `KEY-NAME` and `REGION`, but these default to
empty (no key, you *can not* log in to instances) and
`us-east-1`. (You can also provide these values via environmental
variables AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and
AWS_DEFAULT_REGION.)

This will deploy `freezr-test` CloudFormation stack, run integration
tests against it and finally tear down the stack.

The more manual approach is to deploy the stack yourself, run tests
against it, and tear down the stack when you are done::

  $ export AWS_ACCESS_KEY_ID=<id>
  $ export AWS_SECRET_ACCESS_KEY=<secret>
  $ export AWS_DEFAULT_REGION=<region>
  $ ./deploy
  $ ./tests/freeze-thaw-aws.sh
  $ ./deploy stop

If you want to run individual test sets directly, do::

  $ cd tests
  $ nosetests -x -v freeze_thaw_aws_test/...py
