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

./deploy stop
./deploy

if ./freeze-thaw-aws.sh "$@" 2>&1 | tee ${LOG_PREFIX}integration-test${LOG_SUFFIX}.log; then
    retval=0
else
    retval=1
fi

./deploy stop
exit $retval
