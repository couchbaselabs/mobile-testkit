#!/usr/bin/env bash
# $1 = mobile-testkit branch to check out
# $2 = mode 'cc' or 'di'
# $3 = xattrs flag (--xattrs)
# $4 = Couchbase Server version
# $5 = Sync Gateway version
# $6 = test filter -k "test_pattern"

if [ $# -ne 6 ]
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

# Run single test
pytest -s --mode=$2 $3 --server-version=$4 --sync-gateway-version=$5 $6 testsuites/syncgateway/functional/tests --collect-only
