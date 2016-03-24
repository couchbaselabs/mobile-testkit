#!/usr/bin/env bash

# Generate cluster topologies from a list of machine endpoints (either IPs or AWS)
python2.7 libraries/utilities/generate_clusters_from_pool.py

# Run the sync gateway functional tests
robot testsuites/syncgateway/functional/
