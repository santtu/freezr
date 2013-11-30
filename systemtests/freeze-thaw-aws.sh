#!/bin/bash -e
cur_dir=$(dirname $0)
top_dir=$(dirname $0)/..
test_dir=$cur_dir/freeze_thaw_aws_test
manage="python $top_dir/manage.py"
access_key="${1-$AWS_ACCESS_KEY_ID}"
secret_key="${2-$AWS_SECRET_ACCESS_KEY}"
key_name="${3-default}"
region="${4-${AWS_DEFAULT_REGION-us-east-1}}"
LOG_PREFIX=${LOG_PREFIX-}
LOG_SUFFIX=${LOG_SUFFIX-}
pids=()
pidfile=freeze-thaw-aws.pid

if [ -z "$access_key" -o -z "$secret_key" ]; then
    echo "Usage: $0 [AWS-ACCESS-KEY-ID [AWS-SECRET-ACCESS-KEY \
[KEY-NAME [REGION]]]]

You can also specify these values through environmental variables
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY and AWS_DEFAULT_REGION." >&2
    exit 2
fi

function env_setup {
    source $top_dir/virtualenv/bin/activate
}

function logname {
    echo "${LOG_PREFIX}$1${LOG_SUFFIX}.log"
    return 0
}

function pidof {
    if [[ -z "$1" ]]; then
	echo -n ''
    elif [[ ! "$1" =~ ^[0-9]+$ ]]; then
	pgrep -f "$1" | tr '\n' ' '
    else
	echo -n "$1 "
    fi
    return 0
}

function allpids {
    for pid in "${pids[@]}"; do
	pidof "$pid"
    done
    return 0
}

function terminate {
    set +e
    code="$1"
    [[ ${#pids[@]} == 0 ]] && exit $code
    echo -n "Terminate, killing pids ... "
    # for pid in "${pids[@]}"; do
    # 	pid=$(pidof "$pid")
    for pid in $(allpids); do
	echo -n "$pid "
	(kill -- -$pid; kill $pid; sleep 1;
	    kill -9 -- -$pid; kill -9 $pid) >/dev/null 2>/dev/null
    done

    echo "done"
    pids=()
    rm -f $pidfile

    exit $code
}

function check {
    for pid in "$@"
    do
	if ! kill -0 $(pidof "$pid") >/dev/null 2>&1; then
	    return 1
	fi
    done
    return 0
}

function check_add {
    name="$1"
    pid="$2"
    pids+=("$pid")

    if [ -z "$pid" ]; then
	echo "No child detected ..."
	exit 1
    fi

    if ! check "$pid"; then
	echo "Child $pid ($name) died ..."
	exit 1
    fi

    echo -n $(pidof "$pid")" "

    write_pidfile
}

function write_pidfile {
    echo "$(allpids)" >$pidfile
}

trap 'terminate $?' EXIT
trap 'terminate 1' HUP INT QUIT TERM

# See if there is rabbitmq-server already running, if not, spawn one.
if ! rabbitmqctl status >/dev/null 2>&1; then
    echo -n "RabbitMQ server not running, starting temporary server ... "
    rabbitmq-server >>$(logname rabbitmq) 2>&1 &
    sleep 5; check_add "rabbitmq-server" $!
    echo "done"
fi

if [ -z "$(rabbitmqctl list_vhosts | grep freezr_testing)" ]; then
    echo "Creating freezr_testing vhost on RabbitMQ server ... "
    rabbitmqctl add_vhost freezr_testing
    rabbitmqctl set_permissions -p freezr_testing guest '.*' '.*' '.*'
fi

export PYTHONPATH=$top_dir:$cur_dir
export DJANGO_SETTINGS_MODULE=freeze_thaw_aws_test.settings

# Can't use testserver, it creates in-memory database and celery needs
# access to a real db shared with the server. So setup a new, blank
# database.

env_setup

if [ -n "$USE_EXISTING_FREEZR" ]; then
    echo "Using existing freezr environment"
else
    echo -n "Initializing test database ... "
    (rm -f db.sqlite3 && \
	$manage syncdb --noinput && \
	$manage loaddata $test_dir/fixtures.yaml) >>$(logname freezr) 2>&1
    echo "done"

    # Celery ..
    echo -n "Starting celeryd ... "
    rm -f celeryd.pid
    $manage celeryd --concurrency 1 -B -l debug \
	--pidfile $cur_dir/celeryd.pid >>$(logname celeryd) 2>&1 &
    sleep 5; check_add "manage.py celeryd" "$(cat celeryd.pid)"
    echo "done"

    export AWS_ACCESS_KEY_ID=$access_key
    export AWS_SECRET_ACCESS_KEY=$secret_key
    export AWS_DEFAULT_REGION=$region

    echo -n "Starting application server ... "
    $manage runserver 9000 >>$(logname freezr) 2>&1 &

    # can't use $! here, see https://code.djangoproject.com/ticket/19137
    # the extra sleep is *required*
    sleep 5; check_add "manage.py runserver 9000" 'runserver 9000'
    echo "done"
fi

echo "Starting test suite, child pids are $(allpids)"

# finally we can run nosetests -- use -x due to interdependence of
# tests (if one fails, others might block etc.)
if ! (env_setup && nosetests -x -v -w $test_dir); then
    echo "FAILURE: Tests failed"
    retval=1
else
    echo "SUCCESS: Tests passed"
    retval=0
fi

if [[ $retval -ne 0 && -n "$KEEP_FAILED_FREEZR" ]]; then
    echo "KEEP_FAILED_FREEZR specified, not killing pids $(allpids)"
    pids=()
elif [ -n "$USE_EXISTING_FREEZR" ]; then
    echo "USE_EXISTING_FREEZR specified, not destroying environment"
    pids=() #tautology, pids would be empty at this point anyway
fi

exit $retval
