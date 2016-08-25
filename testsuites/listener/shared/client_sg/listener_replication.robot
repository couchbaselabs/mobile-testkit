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
    [Tags]  Listener  Sync Gateway  Replication
    [Documentation]
    ...  1. Prepare sync-gateway to have 10000 documents.
    ...  2. Create a single shot pull replicator and to pull the docs into a database.
    ...  3. Verify if all of the docs get pulled.
    ...  Referenced issue: couchbase/couchbase-lite-android#955.
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Large Initial Pull Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${False}

Large Initial Continuous Pull Replication
    [Tags]  Listener  Sync Gateway  Replication
    [Documentation]
    ...  1. Prepare sync-gateway to have 10000 documents.
    ...  2. Create a single continuous pull replicator and to pull the docs into a database.
    ...  3. Verify if all of the docs get pulled.
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Large Initial Pull Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${True}

Large Initial One Shot Push Replication
    [Tags]  Listener  Sync Gateway  Replication
    [Documentation]
    ...  1. Prepare LiteServ to have 10000 documents.
    ...  2. Create a single shot push replicator and to push the docs into a sync_gateway database.
    ...  3. Verify if all of the docs get pushed.
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Large Initial Push Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${False}

Large Initial Continuous Push Replication
    [Tags]  Listener  Sync Gateway  Replication
    [Documentation]
    ...  1. Prepare LiteServ to have 10000 documents.
    ...  2. Create continuous push replicator and to push the docs into a sync_gateway database.
    ...  3. Verify if all of the docs get pushed.
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Large Initial Push Replication
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}
    ...  continuous=${True}

Multiple Replications Not Created With Same Properties
    [Tags]  Listener  Sync Gateway  Replication
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
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Multiple Replications Not Created With Same Properties
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}

Multiple Replications Created with Unique Properties
    [Tags]  Listener  Sync Gateway  Replication
    [Documentation]
    ...  Regression test for couchbase/couchbase-lite-java-core#1386
    ...  1. Setup SGW with a remote database name db for an example
    ...  2. Create a local database such as ls_db
    ...  3. Send POST /_replicate with source = ls_db, target = http://localhost:4985/db, continuous = true
    ...  4. Send POST /_replicate with source = ls_db, target = http://localhost:4985/db, continuous = true, doc_ids=["doc1", "doc2"]
    ...  5. Send POST /_replicate with source = ls_db, target = http://localhost:498\5/db, continuous = true, filter="filter1"
    ...  6. Make sure that the session_id from each POST /_replicate are different.
    ...  7. Send GET /_active_tasks to make sure that there are 3 tasks created.
    ...  8. Send 3 POST /_replicate withe the same parameter as Step 3=5 plus cancel=true to stop those replicators
    ...  9. Repeat Step 3 - 8 with source = and target = db for testing the pull replicator.
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Multiple Replications Created with Unique Properties
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}

Replication with Session Cookie
    [Tags]  Listener  Sync Gateway  Replication  Sessions
    [Documentation]
    ...  Regression test for https://github.com/couchbase/couchbase-lite-android/issues/817
    ...  1. SyncGateway Config with guest disabled = true and One user added (e.g. user1 / 1234)
    ...  2. Create a new session on SGW for the user1 by using POST /_session.
    ...     Capture the SyncGatewaySession cookie from the set-cookie in the response header.
    ...  3. Start continuous push and pull replicator on the LiteServ with SyncGatewaySession cookie.
    ...     Make sure that both replicators start correctly
    ...  4. Delete the session from SGW by sending DELETE /_sessions/ to SGW
    ...  5. Cancel both push and pull replicator on the LiteServ
    ...  6. Repeat step 1 and 2
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus-user.json
    Replication with Session Cookie
    ...  ls_url=${ls_url}
    ...  sg_admin_url=${sg_admin_url}
    ...  sg_url=${sg_url}

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
    Set Test Variable  ${sg_admin_url}        ${cluster_hosts["sync_gateways"][0]["admin"]}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}

    Stop Sync Gateway  url=${sg_url}

Teardown Test

    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}