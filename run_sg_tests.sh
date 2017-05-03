#!/usr/bin/env bash

# Exit on failure
set -e

# In case the docker image is not built with the latest testkit checkout
git pull

# Generate cluster configs
python libraries/utilities/generate_clusters_from_pool.py

# Run single test
pytest -s --pdb --mode=cc --xattrs --server-version=5.0.0-2759 --sync-gateway-version=1.4.2-348 -k "test_sg_sdk_interop_unique_docs" testsuites/syncgateway/functional/tests
