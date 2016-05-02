#!/usr/bin/env bash

robot --loglevel INFO -d results \
    -v PLATFORM:macosx \
    -v LITESERV_VERSION:1.2.1-13 \
    -v SYNC_GATEWAY_VERSION:1.2.1-4 \
    testsuites/listener/shared/replication.robot