#!/usr/bin/env bash

robot --loglevel INFO -d results \
    -v PLATFORM:net \
    -v LITESERV_VERSION:1.3.0-15 \
    -v LITESERV_HOST:localhost \
    -v LITESERV_PORT:59840 \
    -v SYNC_GATEWAY_VERSION:1.2.1-4 \
    -v SYNC_GATEWAY_HOST:localhost \
    -v SYNC_GATEWAY_PORT:4984 \
    -v SYNC_GATEWAY_ADMIN_PORT:4985 \
    testsuites/listener/shared/replication.robot