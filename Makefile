# Default target -- just print out short help text
all:
	@echo "## This is a short help on Makefile usage. For more information on how\n\
## freezr is set up, how to deploy it etc. see README.rst file.\n\
##\n\
## Some targets to try out first:\n\
##\n\
##   test	Runs local tests\n\
##   run-fake	Runs the server with a mock AWS backend at \n\
##		http://localhost:8000/\n\
##\n\
## Try: 'make test run-fake', then fire up your browser and\n\
## navigate to http://localhost:8000/ (if you are running this\n\
## inside vagrant, use http://localhost:8080/ instead.)\n\
##"

########################################################################
##
## Redirect regular common idioms to ensure they run in virtualenv.
##

test: virtualenv-actual-test fake-systemtest
fake-systemtest: virtualenv-actual-fake-systemtest
systemtest: virtualenv-actual-systemtest
run: virtualenv-actual-run
run-fake: virtualenv-actual-run-fake

all-test: test systemtest


## Actual backend implementations for common directives, typically
## applied from virtualenv wrapper.

actual-test:
	flake8 --ignore=E221,E701,E202,E123 freezr systemtests setup.py
	./manage.py test -v2

actual-fake-systemtest:
	./systemtests/run-fake-integration-test.sh

actual-systemtest:
	./systemtests/run-integration-test.sh

actual-run:
	./manage.py syncdb -v1 --noinput
	./run

actual-run-fake:
	-./manage.py flush --noinput
	./manage.py syncdb -v1 --noinput
	./manage.py loaddata freezr/app/fixtures/testing_cfn.yaml
	PYTHONPATH=.:systemtests FREEZR_CLOUD_BACKEND=freeze_thaw_aws_test.aws.Mock ./run

########################################################################
##
## Virtualenv setup and use
##

virtualenv: virtualenv/installed.timestamp
virtualenv/installed.timestamp:
	virtualenv virtualenv
	touch virtualenv/installed.timestamp && $(MAKE) virtualenv-setup || (rm -f virtualenv/installed.timestamp; exit 1)

setup:
	pip install -r requirements.txt virtualenvwrapper

virtualenv-%:
	@$(SHELL) -c 'if [ -z "$$VIRTUAL_ENV" ]; then if [ ! -d virtualenv/installed.timestamp ]; then $(MAKE) virtualenv; fi; . virtualenv/bin/activate; fi && $(MAKE) $(subst virtualenv-,,$@) MAKEFLAGS= MAKELEVEL='

########################################################################

.PHONY: actual-test actual-systemtest setup all-test \
	systemtest test run all run-fake virtualenv
