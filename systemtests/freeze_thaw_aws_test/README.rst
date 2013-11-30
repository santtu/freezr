A note on file and test method naming:

* We are abusing unittest framework here to ensure that our
  **integration** tests run in expected order. These intergration
  tests are **not** independent of each other, e.g. they **must** be
  run in a certain order (reset, populate, ...).

* For this end, all test files and test methods contain a number
  prefix to ensure their ordering. All test cases themselves contain
  the """ docstring with the test case number too.

* A lot of unseen work is done in util.Mixin, which should be mixed in
  with the test cases to provide self.client that is correctly set up
  to connect to the test server (default is localhost:9000, but this
  can be overridden via env var `FREEZR_SERVER_HOST` and
  `FREEZR_SERVER_PORT`).

Another note:

* You need to set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` env
  vars, as these are used to create the account during tests.
