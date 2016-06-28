*** Settings ***
Documentation     A test suite containing functional tests of the Listener's
...               replication with sync_gateway

Resource          resources/common.robot
Library           DebugLibrary
Library           Process

Library           OperatingSystem
Library           ${KEYWORDS}/Async.py
Library           ${KEYWORDS}/MobileRestClient.py
Library           ${KEYWORDS}/LiteServ.py
Library           ${KEYWORDS}/Document.py
Library           ${KEYWORDS}/ClusterKeywords.py
Library           ${KEYWORDS}/SyncGateway.py
Library           ${KEYWORDS}/CouchbaseServer.py
Library           ${KEYWORDS}/Logging.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${sg_db}  db

*** Test Cases ***
Large One-Shot Push Replication
    [Documentation]
    ...  Could cause out of memory issue (~4.5KB/doc * 25000 docs)
    ...  original ticket: https://github.com/couchbase/couchbase-lite-android/issues/898
    ...  scenario:
    ...  1. Running sync_gateway or CouchDB 
    ...  2. Create database and create 10000 docs (~4.5KB/doc) at client by REST API
    ...  3. Start one-shot push replication
    ...  4. Make sure out-of-memory exception should not be thrown.
    ...  5. Pass criteria

    ${ls_db} =  Create Database  url=${ls_url}  name=ls_db
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${10000}  id_prefix=ls_db  generator=four_k

    # Start One Shot Push Replication
    Start Replication
    ...  url=${ls_url}
    ...  continuous=${False}
    ...  from_db=${ls_db}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Verify Docs Present  url=${sg_url_admin}  db=${sg_db}   expected_docs=${ls_db_docs}

*** Keywords ***
Setup Test
    ${ls_url} =  Start LiteServ
    ...  platform=${PLATFORM}
    ...  version=${LITESERV_VERSION}
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}
    ...  storage_engine=${LITESERV_STORAGE_ENGINE}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus-revs-limit.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}