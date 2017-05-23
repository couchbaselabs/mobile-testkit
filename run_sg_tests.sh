#!/usr/bin/env bash

# Exit on failure
set -e

# In case the docker image is not built with the latest testkit checkout
git pull

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py

# Run single test
pytest --mode=cc --xattrs --server-version=5.0.0-2873 --sync-gateway-version=1.5.0-375 testsuites/syncgateway/functional/tests
