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

Test Setup        Create Database   ${DBNAME}

# Suite Teardown    Shutdown Listener     ios  ${HOSTNAME}
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Variables ***


*** Test Cases ***
Test multiple client dbs with single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${HOSTNAME}    syncgateway
    [Timeout]        5 minutes
    @{ls_dbs} =  Create Listener Databases  ls_db1  ls_db2
    ${sg_db} =   Create Sync Gateway Database  sg_db1
    Start Continuous Push / Pull Replication  ${ls_dbs[0]}  ${sg_db}
    Start Continuous Push / Pull Replication  ${ls_dbs[1]}  ${sg_db}
    ${ls_db0_docs} =  Add Docs  @{ls_dbs[0]}  ${500}
    ${ls_db1_docs} =  Add Docs  @{ls_dbs[1]}  ${500}
    Verify Number of Docs  @{ls_dbs[0]}  ${500}
    Verify Number of Docs  @{ls_dbs[1]}  ${500}
    @{all_docs} =  Create List  ${ls_db0_docs}  ${ls_db1_docs}
    Verify Docs in Sync Gateway Changes Feed  @{all_docs}
    Verify Docs in LiteServ Database  ${ls_dbs[0]}  @{all_docs}
    Verify Docs in LiteServ Database  ${ls_dbs[1]}  @{all_docs}

*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ
    Start LiteServ
    Install Local Sync Gateway
    Start Sync Gateway  ${SYNC_GATEWAY_CONFIG}

Teardown Suite
    [Documentation]  Shutdown LiteServ and remove the package.
    Shutdown LiteServ
    Shutdown Sync Gateway
    Remove LiteServ
    Remove Synd Gateway

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
