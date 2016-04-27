*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Resource          ./defines.robot
Library           DebugLibrary
Library           Process
Library           ${KEYWORDS}/TKClient.py

Library           ${KEYWORDS}/LiteServ.py
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}
...                 hostname=${LITESERV_HOSTNAME}
...                 port=${LITESERV_PORT}

Library           ${KEYWORDS}/SyncGateway.py
...                 version_build=${SYNC_GATEWAY_VERSION}
...                 hostname=${SYNC_GATEWAY_HOSTNAME}

# Passed in at runtime
#Suite Setup       Setup Suite
#Suite Teardown    Teardown Suite

Test Setup        Setup Test
Test Teardown     Teardown Test


*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/walrus.json

*** Test Cases ***
Test multiple client dbs with single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${HOSTNAME}    syncgateway
    # [Timeout]        5 minutes
    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    ${ls_db1} =  Create Database  url=${ls_url}  name=ls_db1  listener=True
    ${ls_db2} =  Create Database  url=${ls_url}  name=ls_db2  listener=True
    ${sg_db} =   Create Database  url=${sg_url_admin}  name=sg_db

    Start Replication
    ...  url=${ls_url}
    ...  continuous=True
    ...  from_url=${ls_url}  from_db=${ls_db1}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Debug

#    Start Continuous Push / Pull Replication  ${ls_db2}  ${sg_db}

    #${ls_db1_docs} =  Add Docs  url=${ls_url}  db=${ls_db1}  number=${500}  id_prefix=test
    #${ls_db2_docs} =  Add Docs  url=${ls_url}  db=${ls_db2}  number=${500}  id_prefix=test

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
    ${ls_url} =  Start LiteServ
    Set Test Variable  ${ls_url}
    ${sg_url}  ${sg_url_admin} =  Start Sync Gateway  ${SYNC_GATEWAY_CONFIG}
    Set Test Variable  ${sg_url}
    Set Test Variable  ${sg_url_admin}

Teardown Test
    Delete Databases  ${ls_url}
    Delete Databases  ${sg_url_admin}
    Shutdown LiteServ
    Shutdown Sync Gateway


Start LiteServ
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/.
    [Timeout]       1 minute
    ${binary_path} =  Get LiteServ Binary Path
    Start Process   ${binary_path}  -Log  YES  -LogSync  YES  -LogCBLRouter  YES  -LogSyncVerbose  YES  -LogRemoteRequest  YES
    ...             alias=liteserv-ios
    ...             shell=True
    ...             stdout=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stdout.log
    ...             stderr=${RESULTS}/${TEST_NAME}-${PLATFORM}-liteserv-stderr.log
    Process Should Be Running   handle=liteserv-ios
    ${ls_url} =  Verify LiteServ Launched
    [return]  ${ls_url}

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
    ${sg_url} =  Verify Sync Gateway Launched
    [return]    ${sg_url}

Shutdown Sync Gateway
    [Documentation]   Starts LiteServ for a specific platform. The LiteServ binaries are located in deps/binaries.
    [Timeout]       1 minute
    Terminate Process          handle=sync_gateway
    Process Should Be Stopped  handle=sync_gateway



