#!/usr/bin/env bash

# Generate cluster topologies from a list of machine endpoints (either IPs or AWS)
# python libraries/utilities/generate_clusters_from_pool.py

# Run the sync gateway functional tests
robot --loglevel DEBUG \
      -v SYNC_GATEWAY_VERSION:1.2.1-4 \
      -v SERVER_VERSION:4.1.1 \
      -v SYNC_GATEWAY_HOST:localhost \
      -v SYNC_GATEWAY_PORT:4984 \
      -v SYNC_GATEWAY_ADMIN_PORT:4985 \
      testsuites/syncgateway/functional/local_sg_cbs.robot
