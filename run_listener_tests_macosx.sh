#!/usr/bin/env bash

robot --loglevel DEBUG -d results \
    -v PLATFORM:macosx \
    -v LITESERV_VERSION:1.2.1-13 \
    -v LITESERV_HOST:localhost \
    -v LITESERV_PORT:59840 \
    -v SYNC_GATEWAY_VERSION:1.2.1-4 \
    -v SYNC_GATEWAY_HOST:localhost \
    -v SYNC_GATEWAY_PORT:4984 \
    -v SYNC_GATEWAY_ADMIN_PORT:4985 \
    testsuites/listener/shared/replication.robot