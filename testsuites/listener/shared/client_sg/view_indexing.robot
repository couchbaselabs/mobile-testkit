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

Test Setup        Setup Test
Test Teardown     Teardown Test

*** Variables ***
${d_doc_name}  dd


*** Test Cases ***
Stale revision should not be in the index
    [Documentation]
    ...  original ticket: https://github.com/couchbase/couchbase-lite-android/issues/855
    ...  scenario:
    ...  1. Running sync_gateway
    ...  2. Create database and starts both push and pull replicators through client REST API
    ...  3. Create two or more views through client REST API
    ...  4. Add doc, and verify doc is index with current revision through client REST API
    ...  5. Make sure document is pushed to sync gateway through sync gateway REST API
    ...  6. Update doc with sync gateway (not client side) through sync gateway REST API
    ...  7. Make sure updated document is pull replicated to client  through client REST API
    ...  8. Make sure updated document is indexed through client REST API
    ...  9. Make sure stale revision is deleted from index.  through client REST API
    ...  10. Pass criteria

    ${view} =  catenate  SEPARATOR=
    ...  {
    ...    "language" : "javascript",
    ...    "views" : {
    ...        "test_view" : {
    ...            "map" : "function(doc, meta) { emit(doc.content, null); }"
    ...        }
    ...    }
    ...  }

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db
    ${design_doc_id} =  Add Design Doc  url=${ls_url}  db=${ls_db}  name=${d_doc_name}  view=${view}
    ${design_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=${design_doc_id}

    ${doc_body} =  Create Doc  id=doc_1  content={"hi": "I should be in the view"}
    ${doc_body_2} =  Create Doc  id=doc_2
    ${doc} =  Add Doc  url=${ls_url}  db=${ls_db}  doc=${doc_body}
    ${doc} =  Add Doc  url=${ls_url}  db=${ls_db}  doc=${doc_body_2}

    ${rows} =  Get View  url=${ls_url}  db=${ls_db}  design_doc_id=${design_doc_id}  view_name=test_view
    Debug

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

    Set Test Variable  ${num_docs}  ${10}
    Set Test Variable  ${num_revs}  ${100}

    Stop Sync Gateway  url=${sg_url}
    Start Sync Gateway  url=${sg_url}  config=${SYNC_GATEWAY_CONFIGS}/walrus.json

Teardown Test
    Delete Databases  ${ls_url}
    Shutdown LiteServ  platform=${PLATFORM}
    Stop Sync Gateway  url=${sg_url}
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}

