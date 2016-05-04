#!/usr/bin/env bash

robot --loglevel DEBUG -d results \
    -v PLATFORM:android \
    -v LITESERV_VERSION:1.2.1-18 \
    -v LITESERV_HOST:192.168.0.18 \
    -v LITESERV_PORT:5984 \
    -v SYNC_GATEWAY_VERSION:1.2.1-4 \
    -v SYNC_GATEWAY_HOST:192.168.0.14 \
    -v SYNC_GATEWAY_PORT:4984 \
    -v SYNC_GATEWAY_ADMIN_PORT:4985 \
    testsuites/listener/shared/replication.robot