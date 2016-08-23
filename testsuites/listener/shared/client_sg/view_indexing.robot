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
${sg_user_name}  sg_user
${sg_db}  db

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

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=password  channels=${sg_user_channels}
    ${sg_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${view} =  catenate  SEPARATOR=
    ...  {
    ...    "language" : "javascript",
    ...    "views" : {
    ...        "content_view" : {
    ...            "map" : "function(doc, meta) { if (doc.content) { emit(doc._id, doc._rev); } }"
    ...        },
    ...         "update_view" : {
    ...            "map" : "function(doc, meta) { emit(doc.updates, null); }"
    ...        }
    ...    }
    ...  }

    ${ls_db} =       Create Database  url=${ls_url}  name=ls_db

    # Setup continuous push / pull replication from ls_db1 to sg_db
    ${repl_push} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_db=${ls_db}
    ...  to_url=${sg_url_admin}  to_db=${sg_db}

    ${repl_pull} =  Start Replication
    ...  url=${ls_url}
    ...  continuous=${True}
    ...  from_url=${sg_url_admin}  from_db=${sg_db}
    ...  to_db=${ls_db}

    ${design_doc_id} =  Add Design Doc  url=${ls_url}  db=${ls_db}  name=${d_doc_name}  doc=${view}
    ${design_doc} =  Get Doc  url=${ls_url}  db=${ls_db}  doc_id=${design_doc_id}

    ${doc_body} =  Create Doc  id=doc_1  content={"hi": "I should be in the view"}  channels=${sg_user_channels}
    ${doc_body_2} =  Create Doc  id=doc_2  channels=${sg_user_channels}

    ${doc} =  Add Doc  url=${ls_url}  db=${ls_db}  doc=${doc_body}
    ${doc_2} =  Add Doc  url=${ls_url}  db=${ls_db}  doc=${doc_body_2}

    ${content_view_rows} =  Get View  url=${ls_url}  db=${ls_db}  design_doc_id=${design_doc_id}  view_name=content_view
    Verify View Row Num  view_response=${content_view_rows}  expected_num_rows=${1}

    ${update_view_rows} =  Get View  url=${ls_url}  db=${ls_db}  design_doc_id=${design_doc_id}  view_name=update_view
    Verify View Row Num  view_response=${update_view_rows}  expected_num_rows=${2}

    ${expected_docs_list} =  Create List  ${doc}  ${doc_2}
    Verify Docs Present  url=${sg_url}  db=${sg_db}  expected_docs=${expected_docs_list}  auth=${sg_session}

    ${updated_doc} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc["id"]}  number_updates=${10}  auth=${sg_session}

    # Make sure revision sync_to client
    Verify Docs Present  url=${ls_url}  db=${ls_db}  expected_docs=${updated_doc}

    # Verify rows is still one
    ${content_view_rows_2} =  Get View  url=${ls_url}  db=${ls_db}  design_doc_id=${design_doc_id}  view_name=content_view
    Verify View Row Num  view_response=${content_view_rows_2}  expected_num_rows=${1}

    Verify View Contains Keys    view_response=${content_view_rows_2}  keys=${doc["id"]}
    Verify View Contains Values  view_response=${content_view_rows_2}  values=${updated_doc["rev"]}


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

