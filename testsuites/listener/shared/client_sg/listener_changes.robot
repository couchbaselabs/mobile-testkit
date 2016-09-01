*** Settings ***
Documentation     A test suite containing functional tests for the
...               Listener's changes feed

Resource          resources/common.robot

Library           OperatingSystem
Library           ${KEYWORDS}/MobileRestClient.py
Library           ${KEYWORDS}/LiteServ.py
Library           ${KEYWORDS}/ClusterKeywords.py
Library           ${KEYWORDS}/SyncGateway.py
Library           ${KEYWORDS}/Logging.py

Library           listener_changes.py

Test Setup        Setup Test
Test Teardown     Teardown Test
Test Timeout      1 minute

*** Variables ***
${sg_db}  db

*** Test Cases ***
Longpoll Changes Termination Timeout
    [Tags]  sanity  listener  syncgateway  changes
    [Documentation]
    ...  https://github.com/couchbase/couchbase-lite-java-core/issues/1296
    ...  Create 30 longpoll _changes in a loop (with timeout parameter = 5s)
    ...  Cancel the request after 2s
    ...  Wait 5.1s
    ...  Create another request GET /db/ on listener and make sure the listener responds

    Run Keyword If  '${PLATFORM}' == 'android' or '${PLATFORM}' == 'net'
    ...  Longpoll Changes Termination Timeout
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  ELSE
    ...  Fail  Mac OSX fails due to https://github.com/couchbase/couchbase-lite-ios/issues/1236

Longpoll Changes Termination Heartbeat
    [Tags]  sanity  listener  syncgateway  changes
    [Documentation]
    ...  https://github.com/couchbase/couchbase-lite-java-core/issues/1296
    ...  Create 30 longpoll _changes in a loop (with heartbeat parameter = 5s)
    ...  Cancel the request after 2s
    ...  Wait 5.1s
    ...  Create another request GET /db/ on listener and make sure the listener responds

    Run Keyword If  '${PLATFORM}' == 'android' or '${PLATFORM}' == 'net'
    ...  Longpoll Changes Termination Heartbeat
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  ELSE
    ...  Fail  Mac OSX fails due to https://github.com/couchbase/couchbase-lite-ios/issues/1236


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