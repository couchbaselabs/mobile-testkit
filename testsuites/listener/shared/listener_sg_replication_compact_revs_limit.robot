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
${num_docs}  ${100}
${num_revs}  ${120}
${sg_db}     db
${sg_user_name}   sg_user

*** Test Cases ***
Client to Sync Gateway Complex Replication With Revs Limit
    [Documentation]
    [Tags]           sanity     listener    ${PLATFORM}    syncgateway
    #[Timeout]        5 minutes

    Log  Using LiteServ: ${ls_url}
    Log  Using Sync Gateway: ${sg_url}
    Log  Using Sync Gateway: ${sg_url_admin}

    # Test the endpoint, listener does not support users but should have a defaul response
    ${mock_ls_session} =  Get Session  ${ls_url}

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =  Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${sg_doc} =  Add Docs  url=${sg_url}  db=${sg_db}  number=${num_docs}  id_prefix=sg_db  auth=${sg_session}

    Log To Console  ${sg_session}

    ${ls_db1} =  Create Database  url=${ls_url}  name=ls_db1
    ${ls_db1_docs} =  Add Docs  url=${ls_url}  db=${ls_db1}  number=${num_docs}  id_prefix=ls_db1

    # Start replication ls_db1 -> sg_db
    Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_db=${ls_db1}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    Debug


    Verify Docs Present  url=${sg_url_admin}  db=${sg_db}  expected_docs=${ls_db1_docs}


#    ${ls_db1} =  Create Database  url=${ls_url}  name=ls_db1
#    ${ls_db2} =  Create Database  url=${ls_url}  name=ls_db2
#    ${sg_db} =   Create Database  url=${sg_url_admin}  name=sg_db  server=walrus:
#
#    # Setup continuous push / pull replication from ls_db1 to sg_db
#    Start Replication
#    ...  url=${ls_url}
#    ...  continuous=${True}
#    ...  from_db=${ls_db1}
#    ...  to_url=${sg_url_admin}  to_db=${sg_db}
#
#    Start Replication
#    ...  url=${ls_url}
#    ...  continuous=${True}
#    ...  from_url=${sg_url_admin}  from_db=${sg_db}
#    ...  to_db=${ls_db1}
#
#    # Setup continuous push / pull replication from ls_db2 to sg_db
#    Start Replication
#    ...  url=${ls_url}
#    ...  continuous=${True}
#    ...  from_db=${ls_db2}
#    ...  to_url=${sg_url_admin}  to_db=${sg_db}
#
#    Start Replication
#    ...  url=${ls_url}
#    ...  continuous=${True}
#    ...  from_url=${sg_url_admin}  from_db=${sg_db}
#    ...  to_db=${ls_db2}
#
#    ${ls_db1_docs} =  Add Docs  url=${ls_url}  db=${ls_db1}  number=${500}  id_prefix=test_ls_db1
#    ${ls_db2_docs} =  Add Docs  url=${ls_url}  db=${ls_db2}  number=${500}  id_prefix=test_ls_db2
#
#    @{ls_db1_db2_docs} =  Create List  ${ls_db1_docs}  ${ls_db2_docs}
#
#    Verify Docs Present  url=${ls_url}        db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
#    Verify Docs Present  url=${ls_url}        db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}
#    Verify Docs Present  url=${sg_url_admin}  db=${sg_db}   expected_docs=@{ls_db1_db2_docs}
#
#    Verify Docs In Changes  url=${sg_url_admin}  db=${sg_db}   expected_docs=@{ls_db1_db2_docs}
#    Verify Docs In Changes  url=${ls_url}        db=${ls_db1}  expected_docs=@{ls_db1_db2_docs}
#    Verify Docs In Changes  url=${ls_url}        db=${ls_db2}  expected_docs=@{ls_db1_db2_docs}

*** Keywords ***
Setup Test
    ${ls_url} =  Start LiteServ
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/1sg
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus-revs-limit.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}







