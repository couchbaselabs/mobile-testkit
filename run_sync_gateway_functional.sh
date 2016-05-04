#!/usr/bin/env bash

# Generate cluster topologies from a list of machine endpoints (either IPs or AWS)
python libraries/utilities/generate_clusters_from_pool.py

# Run the sync gateway functional tests
robot --loglevel DEBUG \
      -v SYNC_GATEWAY_VERSION:1.2.1-4 \
      -v SERVER_VERSION:4.1.1 \
      -t "test dcp reshard single sg accel goes down and up" testsuites/syncgateway/functional/1sg_2ac_1cbs.robot
