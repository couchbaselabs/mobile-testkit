*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Library           DebugLibrary
Library           Process

Library           ${KEYWORDS}/Async.py
Library           ${KEYWORDS}/MobileRestClient.py
Library           ${KEYWORDS}/LiteServ.py
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}

Library           ${KEYWORDS}/SyncGateway.py
...                 version_build=${SYNC_GATEWAY_VERSION}

Library           ${KEYWORDS}/CouchbaseServer.py

# Passed in at runtime
Suite Setup       Setup Suite

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${SYNC_GATEWAY_CONFIG}  ${SYNC_GATEWAY_CONFIGS}/default.json
${SERVER_BUCKET}        sg-data-bucket

*** Test Cases ***
Replication with multiple client dbs and single sync_gateway db
    [Documentation]
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    [Timeout]        5 minutes

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}

    ${ls_db1} =  Create Database  url=${ls_url}  name=ls_db1
    ${ls_db2} =  Create Database  url=${ls_url}  name=ls_db2

    ${sg_db} =   Create Database  url=${sg_url_admin}  name=sg_db  server=${cbs_url}

    # Setup continuous push / pull replication from ls_db1 to sg_db
    Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_db=${ls_db1}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db1}

    # Setup continuous push / pull replication from ls_db2 to sg_db
    Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_db=${ls_db2}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db2}

    ${ls_db1_docs} =  Add Docs  url=${ls_url}  db=${ls_db1}  number=${500}  id_prefix=test_ls_db1
    ${ls_db2_docs} =  Add Docs  url=${ls_url}  db=${ls_db2}  number=${500}  id_prefix=test_ls_db2

    @{ls_db1_db2_docs} =  Create List  ${ls_db1_docs}  ${ls_db2_docs}

    Verify Docs Present  url=${ls_url}        db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs Present  url=${ls_url}        db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs Present  url=${sg_url_admin}  db=${sg_db}   expected_docs=@{ls_db1_db2_docs}

    Verify Docs In Changes  url=${sg_url_admin}  db=${sg_db}   expected_docs=@{ls_db1_db2_docs}
    Verify Docs In Changes  url=${ls_url}        db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
    Verify Docs In Changes  url=${ls_url}        db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}


*** Keywords ***
Setup Suite
    [Documentation]  Download, install, and launch LiteServ.
    Download LiteServ
    Install LiteServ
    Download Sync Gateway
    ${cbs_url} =  Install Couchbase Server
    ...  hosts=${COUCHBASE_SERVER_HOST}
    ...  version=${COUCHBASE_SERVER_VERSION}
    Set Suite Variable  ${cbs_url}

Setup Test
    Delete Buckets  url=${cbs_url}

    ${ls_url} =  Start LiteServ
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}

    ${sg_url}  ${sg_url_admin} =  Start Sync Gateway
    ...  config=${SYNC_GATEWAY_CONFIG}
    ...  host=${SYNC_GATEWAY_HOST}
    ...  port=${SYNC_GATEWAY_PORT}
    ...  admin_port=${SYNC_GATEWAY_ADMIN_PORT}

    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_url}
    Set Test Variable  ${sg_url_admin}

Teardown Test
    Delete Databases  ${ls_url}
    Delete Databases  ${sg_url_admin}
    Shutdown LiteServ
    Shutdown Sync Gateway







