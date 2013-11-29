#!/bin/bash -e
cur_dir=$(dirname $0)
top_dir=$(dirname $0)/..

export LOG_SUFFIX=${LOG_SUFFIX--$(date +%FT%R)}

(cd $top_dir && ./deploy stop ; ./deploy)
if ./freeze-thaw-aws.sh "$@" 2>&1 | tee integration-test$LOG_SUFFIX.log; then
    retval=0
else
    retval=1
fi
(cd $top_dir && ./deploy stop)
exit $retval
