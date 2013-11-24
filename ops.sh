#!/bin/bash -e
id=${1-1}
base=${OP-$(basename $0 .sh)}
account=
base_url=${base_url-http://localhost:8000/api}
case $base in
    freeze|thaw)
	url=$base_url/project/$id/$base/
	;;
    refresh)
	url=$base_url/account/$id/$base/
	;;
    *)
	echo "ERROR: Operation not defined either via \$OP or symbolic link." >&2
	exit 2
esac

echo '{}' | lwp-request -E -m POST -H 'Accept: application/json' -c 'application/json' $url
exit 0
