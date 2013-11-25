#!/bin/bash -e
top_dir=$(dirname $0)
cfn=$top_dir/lib/testnetworks.cfn.json
cfn_temp=$TMPDIR/testnetworks.cfn.filtered.json

if [ "$1" = "stop" ]; then
    stop=true
    shift
fi
stack=${1-freezr-test}
egrep -v '^[ 	]*//' $cfn >$cfn_temp

function running {
    aws cloudformation describe-stacks --stack-name $stack >/dev/null 2>&1 </dev/null
    return $?
}

if [ -n "$stop" ]; then
    if running; then
	aws cloudformation delete-stack --stack-name $stack
    fi

    exit 0
fi

if ! aws cloudformation validate-template --template-body file://$cfn_temp; then
    echo "ERROR: Template validation failed, processed file in $cfn_temp file." >&2
    exit 1
fi

if running; then
    echo -n 'Stack running, deleting and waiting to terminate '
    aws cloudformation delete-stack --stack-name $stack
    while running
    do
	echo -n "."
	sleep 1
    done
    echo " done"
fi
aws cloudformation create-stack --stack-name $stack --parameters 'ParameterKey=KeyName,ParameterValue=freezr' --template-body file://$cfn_temp
exit 0
