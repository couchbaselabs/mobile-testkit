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

Library           listener_2sgs.py

Test Setup        Setup Test
Test Teardown     Teardown Test
Test Timeout      1 minute

*** Variables ***
${sg_db}  db
${num_docs}  ${500}

*** Test Cases ***
Longpoll Changes Termination Timeout
    [Tags]  sanity  listener  syncgateway  replication
    [Documentation]
    ...  Port of https://github.com/couchbaselabs/sync-gateway-tests/blob/master/tests/cbl-replication-mismatch-2-gateways.js
    ...  Scenario:
    ...    1. Start 2 sync_gateways
    ...    2. Create sg_db_one db on sync_gateway one
    ...    3. Create sg_db_two db on sync_gateway two
    ...    4. Create ls_db_one and ls_db_two on Liteserv
    ...    5. Setup continuous push / pull replication from ls_db_one <-> sg_db_one
    ...    6. Setup continuous push / pull replication from ls_db_two <-> sg_db_two
    ...    7. Setup continuous push / pull replication from sg_db_one <-> ls_db_two
    ...    8. Setup continuous push / pull replication from sg_db_two <-> ls_db_one
    ...    9. Add num_docs / 2 to each liteserv database
    ...    10. Verify each database has num_docs docs
    ...    11. Verify all_docs in all dbs
    ...    12. Verify changes feed for sg_db_one and sg_db_two
    ...    13. Verify chnages feed for ls_db_one and ls_db_two

    Listener Two Sync Gateways
    ...  ls_url=${ls_url}
    ...  cluster_config=${cluster_hosts}
    ...  num_docs=${num_docs}

*** Keywords ***
Setup Test
    ${ls_url} =  Start LiteServ
    ...  platform=${PLATFORM}
    ...  version=${LITESERV_VERSION}
    ...  host=${LITESERV_HOST}
    ...  port=${LITESERV_PORT}
    ...  storage_engine=${LITESERV_STORAGE_ENGINE}
    Set Test Variable  ${ls_url}

    Set Environment Variable  CLUSTER_CONFIG  ${CLUSTER_CONFIGS}/2sgs
    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}

    Set Test Variable  ${cluster_hosts}
    Set Test Variable  ${ls_url}
    Set Test Variable  ${sg_one_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_two_url}        ${cluster_hosts["sync_gateways"][1]["public"]}

    Stop Sync Gateway  url=${sg_one_url}
    Stop Sync Gateway  url=${sg_two_url}
    Start Sync Gateway  url=${sg_one_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json
    Start Sync Gateway  url=${sg_two_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json

Teardown Test

    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_one_url}
    Stop Sync Gateway  url=${sg_two_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}