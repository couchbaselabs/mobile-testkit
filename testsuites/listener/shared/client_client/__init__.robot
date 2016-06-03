*** Settings ***
Resource          resources/common.robot

Suite Setup       Setup Suite

Library           OperatingSystem
Library           ${KEYWORDS}/LiteServ.py

*** Variables ***

*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ  platform=${LITESERV_ONE_PLATFORM}  version=${LITESERV_ONE_VERSION}
    Download LiteServ  platform=${LITESERV_TWO_PLATFORM}  version=${LITESERV_TWO_VERSION}

    Install LiteServ  platform=${LITESERV_ONE_PLATFORM}  version=${LITESERV_ONE_VERSION}
    Install LiteServ  platform=${LITESERV_TWO_PLATFORM}  version=${LITESERV_TWO_VERSION}
