#!/usr/bin/env bash
# $1 = mobile-testkit branch to check out
# $2 = topology to use (ex. base_cc, ci_cc, base_di, ci_di)
# $3 = test command (ex. pytest  -s --mode=di --server-version=4.6.2 --sync-gateway-version=1.4.1-3 testsuites/syncgateway/functional/tests/)

if [ $# -ne 3 ]
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
python libraries/utilities/generate_config_from_sequoia.py --host-file=hosts.json --topology=$2

# pytest command
$3