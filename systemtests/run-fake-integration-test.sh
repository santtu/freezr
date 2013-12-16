#!/bin/bash -e
#
# Almost lke run-integration-tests.sh, except this will use the fake
# EC2 connector instead.
#
cur_dir=$(dirname $0)
top_dir=$cur_dir
cd $cur_dir

logdir=$(date +%FT%R)
export LOG_PREFIX="logs/$logdir/"
export LOG_SUFFIX=${LOG_SUFFIX-}

if [ -n "$LOG_PREFIX" -a ! -d "$LOG_PREFIX" ]; then
    mkdir -p "$LOG_PREFIX"
fi

rm -f logs/latest
ln -s $logdir logs/latest

# How this works:
#
# * AWS_FAKE is for *tests* (see
#   freeze_thaw_aws_test.util.Mixin.__init__) so they will not try to
#   connect to real AWS endpoint to check instance states. Tests will
#   otherwise connect to the running freezr environment.
#
# * FREEZR_CLOUD_BACKEND environmental variable changes (in
#   freeze_thaw_aws_test.settings) the freezr runtime environment (not
#   the tests, AWS_FAKE is for that) to use a cloud backend which will
#   override the EC2 connection mechanism to "fake" AWS state
#   internally.

export AWS_FAKE=1
export FREEZR_CLOUD_BACKEND=freeze_thaw_aws_test.aws.Mock
export AWS_ACCESS_KEY_ID=none  		# keep freeze-thaw-aws.sh happy
export AWS_SECRET_ACCESS_KEY=none  	# ditto

./freeze-thaw-aws.sh "$@" 2>&1 | tee ${LOG_PREFIX}integration-test${LOG_SUFFIX}.log
retval=${PIPESTATUS[0]}

if [[ $retval -ne 0 ]]; then
    echo "Failure"
fi

exit $retval
