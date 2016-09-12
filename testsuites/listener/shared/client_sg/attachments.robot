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
Library           attachments.py

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${sg_db}  db

*** Test Cases ***

Test Inline Large Attachments
    [Tags]  sanity  listener  syncgateway  attachments  replication
    ...  1.  Start LiteServ and Sync Gateway
    ...  2.  Create 2 databases on LiteServ (ls_db1, ls_db2)
    ...  3.  Start continuous push replication from ls_db1 to sg_db
    ...  4.  Start continuous pull replication from sg_db to ls_db2
    ...  5.  PUT 5 large inline attachments to ls_db1
    ...  6.  DELETE the docs on ls_db1
    ...  7.  PUT same 5 large inline attachments to ls_db1
    ...  8.  Verify docs replicate to ls_db2
    ...  9.  Purge ls_db1
    ...  10. Verify docs removed
    Test Inline Large Attachments
    ...  liteserv_url=${ls_url}
    ...  cluster=${cluster_hosts}

Test Raw attachment
    [Tags]  sanity  listener  syncgateway  attachments
    [Documentation]
    ...  1.  Add Text attachment to sync_gateway
    ...  2.  Try to get the raw attachment
    ...  Pass: It is possible to get the raw attachment

    ${ls_db} =  Create Database  url=${ls_url}  name=ls_db

    ${ls_user_channels} =  Create List  NBC
    ${doc_with_att} =  Create Doc  id=att_doc  content={"sample_key": "sample_val"}  attachment_name=sample_text.txt  channels=${ls_user_channels}
    ${doc} =  Add Doc  url=${ls_url}  db=${ls_db}  doc=${doc_with_att}

    ${attachment} =  Get Attachment  url=${ls_url}  db=${ls_db}  doc_id=${doc["id"]}  attachment_name=sample_text.txt

    ${expected_text} =  Catenate  SEPARATOR=\n
    ...  Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    ...  Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
    ...  Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
    ...  Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.

    Should Be Equal  ${expected_text}  ${attachment}

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
    Set Test Variable  ${cluster_hosts}

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