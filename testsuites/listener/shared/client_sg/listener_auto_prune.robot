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

    Set Test Variable  ${num_docs}  ${100}
    Set Test Variable  ${num_revs}  ${100}

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=ls_db  channels=${sg_user_channels}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}

    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}


Test Auto Prune With Pull Replication
    [Documentation]  Tests that auto prune is happing after a pull replication
    ...  1. Create a database on LiteServ (ls_db)
    ...  2. Add docs tp ls_db
    ...  3. Set up push replication to sync_gateway
    ...  4. Update docs on sync_gateway
    ...  5. Update docs on LiteServ
    ...  6. Set up push replication from sync_gateway
    ...  7. Verify number of revisions on client is default (20)

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    Log  Using Sync Gateway: ${sg_url_admin}

    Set Test Variable  ${num_docs}  ${1}
    Set Test Variable  ${num_revs}  ${50}

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

    ${sg_docs_update} =      Update Docs  url=${sg_url}  db=${sg_db}  docs=${ls_db_docs}  number_updates=${num_revs}  delay=${0.1}  auth=${sg_session}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}  delay=${0.1}

    # Start replication ls_db <- sg_db
    ${repl2} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db}

    Wait For Replication Status Idle  url=${ls_url}  replication_id=${repl1}
    Wait For Replication Status Idle  url=${ls_url}  replication_id=${repl2}

    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}


Test Auto Prune Listener Keeps Conflicts Sanity
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

    Set Test Variable  ${num_docs}  ${1}
    Set Test Variable  ${num_revs}  ${100}

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db

    # Create docs with same prefix to create conflicts when the dbs complete 1 shot replication
    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=doc  channels=${sg_user_channels}
    ${ls_db_docs} =  Add Docs  url=${sg_url}  db=${sg_db}  number=${num_docs}  id_prefix=doc  channels=${sg_user_channels}  auth=${sg_session}

    # Setup one shot pull replication and wait for idle.
    ${repl_id} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${False}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db}

    Wait For No Replications  url=${ls_url}

    # There should now be a conflict on the client
    ${conflicting_revs} =  Get Conflict Revs  url=${ls_url}  db=${ls_db}  doc=${ls_db_docs[0]}

    # Get the doc with conflict rev
    ${conflict_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=${ls_db_docs[0]["id"]}  rev=${conflicting_revs[0]}

    # Update doc past revs limit and make sure conflict is still available
    ${updated_doc} =  Update Doc  url=${ls_url}  db=${ls_db}  doc_id=${ls_db_docs[0]["id"]}  number_updates=${num_revs}
    ${conflict_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=${ls_db_docs[0]["id"]}  rev=${conflicting_revs[0]}

    # Delete doc and ensure that the conflict is now the current rev
    ${deleted_doc} =  Delete Doc  url=${ls_url}  db=${ls_db}  doc_id=${ls_db_docs[0]["id"]}  rev=${updated_doc["rev"]}
    ${current_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=${ls_db_docs[0]["id"]}
    Should Be Equal  ${current_doc["_rev"]}  ${conflicting_revs[0]}


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
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}
