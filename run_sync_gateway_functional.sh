#!/usr/bin/env bash

# Generate cluster topologies from a list of machine endpoints (either IPs or AWS)
python libraries/utilities/generate_clusters_from_pool.py

# Run the sync gateway functional tests
robot --loglevel DEBUG \
      -v SYNC_GATEWAY_VERSION:1.2.0-79 \
      -v SERVER_VERSION:4.1.0 \
      -t "Test Replication Config" testsuites/syncgateway/functional/2sg_1cbs.robot
