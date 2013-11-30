#!/bin/bash -e
cur_dir=$(dirname $0)
top_dir=$cur_dir
cd $cur_dir

logdir=$(date +%FT%R)
export LOG_PREFIX="logs/$logdir/"
export LOG_SUFFIX=${LOG_SUFFIX-}

# export LOG_PREFIX=
# export LOG_SUFFIX=${LOG_SUFFIX--$(date +%FT%R)}

if [ -n "$LOG_PREFIX" -a ! -d "$LOG_PREFIX" ]; then
    mkdir -p "$LOG_PREFIX"
fi

rm -f logs/latest
ln -s $logdir logs/latest

if [ -z "$USE_EXISTING_FREEZR" ]; then
    ./deploy stop
    ./deploy
fi

./freeze-thaw-aws.sh "$@" 2>&1 | tee ${LOG_PREFIX}integration-test${LOG_SUFFIX}.log
retval=${PIPESTATUS[0]}

if [[ -n "$USE_EXISTING_FREEZR" || \
    ( $retval -ne 0 && -n "$KEEP_FAILED_FREEZR" ) ]]; then
    echo "Failure, but not destroying stack"
else
    echo "Destroying stack"
    ./deploy stop
fi

exit $retval
