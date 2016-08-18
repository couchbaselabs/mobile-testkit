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
Library           listener_replication.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${sg_db}  db
${num_docs}  ${10000}

*** Test Cases ***
Large Initial One Shot Pull Replication
    [Documentation]
    ...  1. Prepare sync-gateway to have 10000 documents.
    ...  2. Create a single shot pull replicator and to pull the docs into a database.
    ...  3. Verify if all of the docs get pulled.
    ...  Referenced issue: couchbase/couchbase-lite-android#955.
    Large Initial Pull Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${False}

Large Initial Continuous Pull Replication
    [Documentation]
    ...  1. Prepare sync-gateway to have 10000 documents.
    ...  2. Create a single continuous pull replicator and to pull the docs into a database.
    ...  3. Verify if all of the docs get pulled.
    Large Initial Pull Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${True}

Large Initial One Shot Push Replication
    [Documentation]
    ...  1. Prepare LiteServ to have 10000 documents.
    ...  2. Create a single shot push replicator and to push the docs into a sync_gateway database.
    ...  3. Verify if all of the docs get pushed.
    Large Initial Push Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${False}

Large Initial Continuous Push Replication
    [Documentation]
    ...  1. Prepare LiteServ to have 10000 documents.
    ...  2. Create continuous push replicator and to push the docs into a sync_gateway database.
    ...  3. Verify if all of the docs get pushed.
    Large Initial Push Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${True}

Multiple Replications Not Created With Same Properties
    [Documentation]
    ...  Regression test for https://github.com/couchbase/couchbase-lite-android/issues/939
    ...  1. Create LiteServ database and launch sync_gateway with database
    ...  2. Start 5 continuous push replicators with the same source and target
    ...  3. Make sure the sample replication id is returned
    ...  4. Check that 1 one replication exists in 'active_tasks'
    ...  5. Stop the replication with POST /_replicate cancel=true
    ...  6. Start 5 continuous pull replicators with the same source and target
    ...  7. Make sure the sample replication id is returned
    ...  8. Check that 1 one replication exists in 'active_tasks'
    ...  9. Stop the replication with POST /_replicate cancel=true
    Multiple Replications Not Created With Same Properties
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}



*** Keywords ***
Setup Test
    ${ls_url} =  Start LiteServ
    ...  platform=${PLATFORM}
    ...  version=${LITESERV_VERSION}
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}
    ...  storage_engine=${LITESERV_STORAGE_ENGINE}
    Set Test Variable  ${ls_url}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${cluster_hosts}
    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}


    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json

Teardown Test

    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}