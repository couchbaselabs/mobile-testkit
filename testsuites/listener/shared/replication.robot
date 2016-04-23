*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Resource          ./defines.robot
Library           DebugLibrary
Library           Process
Library           Listener              ${HOSTNAME}     ${PORT}
Suite Setup       Start Listener        ios  ${HOSTNAME}
Test Setup        Create Database       ${DBNAME}


Suite Teardown    Shutdown Listener     ios  ${HOSTNAME}
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Test Cases ***
Test multiple client dbs with single sync_gateway db
    [Documentation]
    [Tags]           Sanity    CBL    Listener    Replication
    [Timeout]        5 minutes

*** Keywords ***
Install Listener
    [Documentation]  Downloads a Listener to deps/ for the platform and version specified
    [Arguments]  ${platform}  ${version}


Start Listener
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Arguments]     ${platform}     ${hostname}
    [Timeout]       1 minute
    Start Process   deps/couchbase-lite-macosx-enterprise_1.2.1-13/LiteServ
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=liteserv-ios-stdout.log
    ...             stderr=liteserv-ios-stderr.log
    Process Should Be Running   handle=liteserv-ios
    Sleep  5s
    Verify Listener Launched

Shutdown Listener
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Arguments]     ${platform}     ${hostname}
    [Timeout]       1 minute
    Terminate Process          handle=liteserv-ios
    Process Should Be Stopped  handle=liteserv-ios
