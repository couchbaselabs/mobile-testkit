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

Library           ${KEYWORDS}/ClusterKeywords.py
Library           ${KEYWORDS}/SyncGateway.py
Library           ${KEYWORDS}/CouchbaseServer.py
Library           ${KEYWORDS}/Logging.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variable ***
${sg_db}            db
${sg_user_name}     sg_user

*** Test Cases ***
Verify Open Revs With Revs Limit Push Conflict
    [Documentation]  https://github.com/couchbase/couchbase-lite-ios/issues/1277
    [Tags]           sanity     listener    syncgateway  replication
    [Timeout]        5 minutes

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    Log  Using Sync Gateway: ${sg_url_admin}

    # Test the endpoint, listener does not support users but should have a default response
    ${mock_ls_session} =  Get Session  ${ls_url}

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=ls_db  channels=${sg_user_channels}

    # Start replication ls_db -> sg_db
    ${repl1} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_db=${ls_db}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Verify Docs Present  url=${sg_url_admin}  db=${sg_db}  expected_docs=${ls_db_docs}

    ${sg_docs_update} =  Update Docs  url=${sg_url}  db=${sg_db}  docs=${ls_db_docs}  number_updates=${num_revs}  auth=${sg_session}
    ${sg_current_doc} =  Get Doc  url=${sg_url}  db=${sg_db}  doc_id=ls_db_2  auth=${sg_session}

    ${ls_db_docs_update} =  Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}
    ${ls_current_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=ls_db_2

    Wait For Replication Status Idle  url=${ls_url}  replication_id=${repl1}

    Log  ${sg_current_doc}
    Log  ${ls_current_doc}

    Verify Doc Rev Generation  url=${ls_url}  db=${ls_db}  doc_id=${ls_current_doc["_id"]}  expected_generation=${21}
    Verify Doc Rev Generation  url=${sg_url}  db=${sg_db}  doc_id=${sg_current_doc["_id"]}  expected_generation=${21}  auth=${sg_session}

    ${expected_ls_revs} =  Create List  ${ls_current_doc["_rev"]}
    Verify Open Revs  url=${ls_url}  db=${ls_db}  doc_id=${ls_current_doc["_id"]}  expected_open_revs=${expected_ls_revs}

    ${expected_sg_revs} =  Create List  ${ls_current_doc["_rev"]}  ${sg_current_doc["_rev"]}
    Verify Open Revs  url=${sg_url_admin}  db=${sg_db}  doc_id=${sg_current_doc["_id"]}  expected_open_revs=${expected_sg_revs}


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

    Set Test Variable  ${num_docs}  ${100}
    Set Test Variable  ${num_revs}  ${20}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}







