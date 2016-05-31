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
...                 platform=${PLATFORM}
...                 version_build=${LITESERV_VERSION}

Library           ${KEYWORDS}/SyncGateway.py
Library           ${KEYWORDS}/CouchbaseServer.py
Library           ${KEYWORDS}/Logging.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variable ***
${sg_db}            db
${sg_user_name}     sg_user

*** Test Cases ***
Client to Sync Gateway Complex Replication With Revs Limit
    [Documentation]
    ...  1.  Clear server buckets
    ...  2.  Restart liteserv with _session
    ...  3.  Restart sync_gateway wil that config
    ...  4.  Create db on LiteServ
    ...  5.  Add numDocs to LiteServ db
    ...  6.  Setup push replication from LiteServ db to sync_gateway
    ...  7.  Verify doc present on sync_gateway (number of docs)
    ...  8.  Update sg docs numRevs * 4 = 480
    ...  9.  Update docs on LiteServ db numRevs * 4 = 480
    ...  10. Setup pull replication from sg -> liteserv db
    ...  11. Verify all docs are replicated
    ...  12. compact LiteServ db (POST _compact)
    ...  13. Verify number of revs in LiteServ db (?revs_info=true) check rev status == available fail if revs available > revs limit
    ...  14. Delete LiteServ db conflicts (?conflicts=true) DELETE _conflicts
    ...  15. Create numDoc number of docs in LiteServ db
    ...  16. Update LiteServ db docs numRevs * 5 (600)
    ...  17. Verify LiteServ db revs is < 602
    ...  18. Verify LiteServ db docs revs prefix (9 * numRevs + 3)
    ...  19. Compact LiteServ db
    ...  20. Verify number of revs <= 10
    ...  21. Delete LiteServ docs
    ...  22. Delete Server bucket
    ...  23. Delete LiteServ db
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    #[Timeout]        5 minutes

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

    ${sg_docs_update} =      Update Docs  url=${sg_url}  db=${sg_db}  docs=${ls_db_docs}  number_updates=${num_revs}  auth=${sg_session}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}

    # Start replication ls_db <- sg_db
    ${repl2} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db}

    Wait For Replication Status Idle  url=${ls_url}  replication_id=${repl2}

    Compact Database  url=${ls_url}  db=${ls_db}

    # After compaction, Mac OSX LiteServ should only have 20 revisions due to built in client revs limit
    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}

    # Sync Gateway should have 70 or 20 revisions due to the specified revs_limit in the sg config and possible conflict winners from the liteserv db
    Verify Max Revs Num For Docs  url=${sg_url}  db=${sg_db}  docs=${ls_db_docs}  expected_max_number_revs_per_doc=${70}  auth=${sg_session}

    Delete Conflicts  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}

    ${expected_generation} =  Evaluate  ${num_revs}+${1}
    Verify Doc Rev Generations  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_generation=${expected_generation}
    Verify Doc Rev Generations  url=${sg_url}  db=${sg_db}  docs=${ls_db_docs}  expected_generation=${expected_generation}  auth=${sg_session}

    Delete Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}
    Verify Docs Deleted  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}
    Verify Docs Deleted  url=${sg_url_admin}  db=${sg_db}  docs=${ls_db_docs}

    ${ls_db_docs} =  Add Docs  url=${ls_url}  db=${ls_db}  number=${num_docs}  id_prefix=ls_db  channels=${sg_user_channels}

    ${double_updates} =  Evaluate  ${num_revs}*2
    ${expected_revs} =  Evaluate  ${num_revs}+${20}+${2}
    ${ls_db_docs_update} =   Update Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  number_updates=${num_revs}

    Verify Max Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_max_number_revs_per_doc=${expected_revs}

    ${expected_generation} =  Evaluate  ${num_revs}*${2}+${3}
    Verify Doc Rev Generations  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_generation=${expected_generation}

    Compact Database  url=${ls_url}  db=${ls_db}

    Verify Revs Num For Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}  expected_revs_per_doc=${20}

    Delete Docs  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}
    Verify Docs Deleted  url=${sg_url_admin}  db=${sg_db}  docs=${ls_db_docs}
    Verify Docs Deleted  url=${ls_url}  db=${ls_db}  docs=${ls_db_docs}


*** Keywords ***
Setup Test
    ${ls_url} =  Start LiteServ
    ...  platform=${PLATFORM}
    ...  version=${LITESERV_VERSION}
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    ${num_docs} =  Set Variable If
    ...  "${PROFILE}" == "sanity"   ${10}
    ...  "${PROFILE}" == "nightly"  ${100}
    ...  "${PROFILE}" == "release"  ${1000}
    Set Test Variable  ${num_docs}

    ${num_revs} =  Set Variable If
    ...  "${PROFILE}" == "sanity"   ${100}
    ...  "${PROFILE}" == "nightly"  ${1000}
    ...  "${PROFILE}" == "release"  ${10000}
    Set Test Variable  ${num_revs}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus-revs-limit.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}







