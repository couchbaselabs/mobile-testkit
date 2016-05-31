*** Settings ***
Resource          resources/common.robot

Suite Setup       Setup Suite

Library           OperatingSystem
Library           ${KEYWORDS}/LiteServ.py

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/walrus.json

*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ  platform=${PLATFORM}  version_build=${LITESERV_VERSION}
    Install LiteServ  platform-${PLATFORM}  version_build=${LITESERV_VERSION}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    Install Sync Gateway  version=${SYNC_GATEWAY_VERSION}  config=${SYNC_GATEWAY_CONFIG}
