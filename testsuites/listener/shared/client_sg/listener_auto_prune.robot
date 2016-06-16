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

*** Variables ***
${sg_db}            db
${sg_user_name}     sg_user

*** Test Cases ***
Test Auto Prune Listener Sanity
    [Documentation]  Test to verify auto pruning is working for the listener
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    [Timeout]        5 minutes

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    Log  Using Sync Gateway: ${sg_url_admin}


    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=ls_db  channels=${sg_user_channels}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}

    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}

Test Auto Prune Listener Keeps Confilts Sanity
    [Documentation]  Test to verify auto pruning is working for the listener
    ...  1. Create db on LiteServ and add docs
    ...  2. Create db on sync_gateway and add docs with the same id
    ...  3. Create one shot push / pull replication
    ...  4. Update LiteServ 50 times
    ...  5. Assert that pruned conflict is still present
    ...  6. Delete the current revision and check that a GET returns the old conflict as the current rev
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    [Timeout]        5 minutes

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    Log  Using Sync Gateway: ${sg_url_admin}


    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=ls_db  channels=${sg_user_channels}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}

    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}

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
    Set Test Variable  ${num_revs}  ${100}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus-revs-limit.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}
