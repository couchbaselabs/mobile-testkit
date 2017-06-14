#!/usr/bin/env bash
# $1 = mobile-testkit branch to check out
# $2 = stream test output flag (-s)
# $3 = mode 'cc' or 'di'
# $4 = xattrs flag (--xattrs)
# $5 = Couchbase Server version
# $6 = Sync Gateway version
# $7 = test filter -k "test_pattern"
# $8 = Suite to run (ex. testsuites/syncgateway/functional/tests)
# $9 = sg lb flag

if [ $# -ne 9 ]
  then
    echo "Did not find all expected args. Please look in the script to see what is required."
    echo "Exiting ..."
    exit 1
fi

# Fail script if any steps fail
set -e

# Print each command
set -x

# Pull repo changes since last docker image build
git pull
git checkout $1

# Instal repo requirements
# This may have changed sinces last docker image build
pip install -r requirements.txt

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py

# Run tests (--ci)
pytest --ci $2 --mode=$3 $4 --server-version=$5 --sync-gateway-version=$6 $7 $8 $9