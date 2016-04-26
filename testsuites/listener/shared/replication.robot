*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Resource          ./defines.robot
Library           DebugLibrary
Library           Process
Library           LiteServ
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}
...                 hostname=${HOSTNAME}
...                 port=${PORT}

# Passed in at runtime
Suite Setup       Setup Suite
Suite Teardown    Teardown Suite

#Test Setup        Create Database   ${DBNAME}

# Suite Teardown    Shutdown Listener     ios  ${HOSTNAME}
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Variables ***


*** Test Cases ***
Test multiple client dbs with single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${HOSTNAME}    syncgateway
    [Timeout]        5 minutes


*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ
    Start LiteServ

Teardown Suite
    [Documentation]  Shutdown LiteServ and remove the package.
    Shutdown LiteServ
    Remove LiteServ

Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Timeout]       1 minute
    ${binary_path} =  Get Binary Path
    Start Process   ${binary_path}
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=liteserv-ios-stdout.log
    ...             stderr=liteserv-ios-stderr.log
    Process Should Be Running   handle=liteserv-ios
    Verify LiteServ Launched

Shutdown LiteServ
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Timeout]       1 minute
    Terminate Process          handle=liteserv-ios
    Process Should Be Stopped  handle=liteserv-ios
