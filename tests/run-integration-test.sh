#!/bin/bash -e
cur_dir=$(dirname $0)
top_dir=$(dirname $0)/..
if [ "$#" -lt 2 ]; then
    echo "Usage: $0 AWS-ACCESS-KEY AWS-SECRET-KEY [KEY-NAME [REGION]] " >&2
    exit 2
fi
access_key="$1"
secret_key="$2"
key_name="${3-}"
region="${4-us-east-1}"

export AWS_DEFAULT_REGION=$region
export AWS_ACCESS_KEY_ID=$access_key
export AWS_SECRET_ACCESS_KEY=$secret_key

export LOG_SUFFIX=${LOG_SUFFIX--$(date +%FT%R)}

(cd $top_dir && ./deploy stop ; ./deploy)
if ./freeze-thaw-aws.sh "$access_key" "$secret_key" "$key_name" "$region" 2>&1 | tee integration-test$LOG_SUFFIX.log; then
    retval=0
else
    retval=1
fi
(cd $top_dir && ./deploy stop)
exit $retval
