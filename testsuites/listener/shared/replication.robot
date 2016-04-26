*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Resource          ./defines.robot
Library           DebugLibrary
Library           Process
Library           ${KEYWORDS}/LiteServ.py
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}
...                 hostname=${HOSTNAME}
...                 port=${PORT}
Library           ${KEYWORDS}/SyncGateway.py
...                 version_build=${SYNC_GATEWAY_VERSION}

# Passed in at runtime
Suite Setup       Setup Suite
Suite Teardown    Teardown Suite

Test Setup        Setup Test
Test Teardown     Teardown Test

# Suite Teardown    Shutdown Listener     ios  ${HOSTNAME}
Test Timeout      30 seconds     The default test timeout elapsed before the test completed.

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/walrus.json

*** Test Cases ***
Test multiple client dbs with single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${HOSTNAME}    syncgateway
    [Timeout]        5 minutes
    Log To Console  Testing ...
#    ${ls_db1} =  Create LiteServ Database  name=ls_db1
#    ${ls_db2} =  Create LiteServ Database  name=ls_db2
#    ${sg_db} =   Create Sync Gateway Database  name=sg_db1
#    Start Continuous Push / Pull Replication  ${ls_db1}  ${sg_db}
#    Start Continuous Push / Pull Replication  ${ls_db2}  ${sg_db}
#    ${ls_db1_docs} =  Add Docs  ${ls_db1}  ${500}
#    ${ls_db2_docs} =  Add Docs  ${ls_db2}  ${500}
#    Verify Number of Docs  ${ls_db1}  ${500}
#    Verify Number of Docs  ${ls_db2}  ${500}
#    @{all_docs} =  Create List  ${ls_db0_docs}  ${ls_db1_docs}
#    Verify Docs in Sync Gateway Changes Feed  @{all_docs}
#    Verify Docs in LiteServ Database  ${ls_dbs[0]}  @{all_docs}
#    Verify Docs in LiteServ Database  ${ls_dbs[1]}  @{all_docs}

*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ
    Download Sync Gateway

Teardown Suite
    [Documentation]  Shutdown LiteServ and remove the package.
    Remove LiteServ
    Remove Sync Gateway

Setup Test
    Start LiteServ
    Start Sync Gateway  ${SYNC_GATEWAY_CONFIG}
    Debug

Teardown Test
    Shutdown LiteServ
    Shutdown Sync Gateway

Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path
    Start Process   ${binary_path}
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stderr.log
    Process Should Be Running   handle=liteserv-ios
    Verify LiteServ Launched

Shutdown LiteServ
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=liteserv-ios
    Process Should Be Stopped  handle=liteserv-ios

Start Sync Gateway
    [Documentation]   Starts sync_gateway with a provided configuration. The sync_gateway binary is located in deps/binaries.
    [Timeout]       1 minute
    [Arguments]  ${sync_gateway_config}
    ${binary_path} =  Get Sync Gateway Binary Path
    Start Process   ${binary_path}  ${sync_gateway_config}
    ...             alias=sync_gateway
    ...             stdout=${RESULTS}/${TEST_NAME}-sync-gateway-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-sync-gateway-stderr.log
    Process Should Be Running   handle=sync_gateway
    Verify Sync Gateway Launched

Shutdown Sync Gateway
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=sync_gateway
    Process Should Be Stopped  handle=sync_gateway



