*** Settings ***
Resource          resources/common.robot

Suite Setup       Setup Suite

Library           OperatingSystem
Library           ${KEYWORDS}/LiteServ.py
Library           ${KEYWORDS}/SyncGateway.py

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/walrus.json

*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ  platform=${PLATFORM}  version=${LITESERV_VERSION}
    Install LiteServ   platform=${PLATFORM}  version=${LITESERV_VERSION}  storage_engine=${LITESERV_STORAGE_ENGINE}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    Clean Cluster
    Install Sync Gateway  sync_gateway_version=${SYNC_GATEWAY_VERSION}  sync_gateway_config=${SYNC_GATEWAY_CONFIG}
