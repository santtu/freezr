#!/bin/bash -e
cur_dir=$(dirname $0)
test_dir=$cur_dir/freeze_thaw_aws_test
top_dir=$(dirname $0)/..
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 AWS-ACCESS-KEY AWS-SECRET-KEY [KEY-NAME [REGION]] " >&2
    exit 2
fi
access_key="$1"
secret_key="$2"
key_name="${3-default}"
region="${4-us-east-1}"
pids=""

function env_setup {
    source $top_dir/virtualenv/bin/activate
}

function terminate {
    code="$1"
    if [ -n "$pids" ]; then
	kill $pids
    fi
    sleep 1
    exit $code
}

function check {
    for pid in "$@"
    do
	if ! kill -0 $pid >/dev/null 2>&1; then
	    return 1
	fi
    done
    return 0
}

function check_add {
    pid="$1"
    pids="$pids $pid"

    sleep 5
    if ! check $pid; then
	echo "Child $pid died ..."
	exit 1
    fi
}

trap 'terminate $?' 0 1 2 15

# If someone knows how to disable plugins from command line or config,
# and not globally via rabbitmq-plugin disable that would be nice to
# know ...
RABBITMQ_NODENAME=freezr RABBITMQ_SERVER_START_ARGS="-rabbitmq_management listener [{port,9002}] -rabbitmq_stomp tcp_listeners [9003] -rabbitmq_mqtt tcp_listeners [9004] " RABBITMQ_NODE_PORT=9001 rabbitmq-server &
check_add $!

export PYTHONPATH=$top_dir/freezr:$cur_dir
(env_setup && $top_dir/freezr/manage.py testserver --addrport=9000 --settings freeze_thaw_aws_test.settings $test_dir/fixtures.yaml) &

# can't use $! here, see https://code.djangoproject.com/ticket/19137
# the extra sleep is *required*
sleep 1; check_add $(pgrep -f freeze_thaw_aws_test.settings)

# finally we can run nosetests
if ! (env_setup && nosetests -w $test_dir); then
    echo "FAILURE: Tests failed"
    exit 1
fi

exit 0
