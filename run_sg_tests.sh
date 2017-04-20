#!/usr/bin/env bash

# Exit on failure
set -e

# In case the docker image is not built with the latest testkit checkout
git pull

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py

# Run single test
pytest -s --mode=cc --server-version=4.6.1 --sync-gateway-version=1.4.0.2-3 testsuites/syncgateway/functional/tests
