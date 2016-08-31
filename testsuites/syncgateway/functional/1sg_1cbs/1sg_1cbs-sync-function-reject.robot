*** Settings ***
Resource          resources/common.robot

Library     DebugLibrary
Library     OperatingSystem

Library     ${Libraries}/NetworkUtils.py
Library     ${KEYWORDS}/Logging.py
Library     ${Keywords}/CouchbaseServer.py
Library     ${Keywords}/SyncGateway.py
Library     ${Keywords}/MobileRestClient.py
Library     ${Keywords}/Document.py

Test Setup      Setup Test
Test Teardown   Teardown Test


*** Test Cases ***
Test Attachments on Docs Rejected By Sync Function
    [Documentation]
    ...  1. Start sync_gateway with sync function that rejects all writes:
    ...  function(doc, oldDoc) {
    ...    throw({forbidden:"No writes!"});
    ...  }
    ...  2. Create a doc with attachment
    ...  3. Use CBS sdk to see if attachment doc exists.  Doc ID will look like _sync:att:sha1-Kq5sNclPz7QV2+lfQIuc6R7oRu0= (where the suffix is the digest)
    ...  4. Assert att doc does not exist
    [Tags]  sanity  attachments  syncgateway  sync

    Set Test Variable  ${sg_user_name}  sg_user
    Set Test Variable  ${sg_uset_password}  password

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=${sg_uset_password}  channels=${sg_user_channels}
    ${sg_user_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    # Verify all docs are getting rejected
    Set Test Variable  ${expected_error}  HTTPError: 403 Client Error: Forbidden for url:*
    Run Keyword And Expect Error  ${expected_error}  Add Docs
    ...  url=${sg_url}  db=${sg_db}  number=${100}  id_prefix=sg_db  channels=${sg_user_channels}  auth=${sg_user_session}

    # Create doc with attachment and push to sync_gateway
    ${doc_with_att} =  Create Doc  id=att_doc  content={"sample_key": "sample_val"}  attachment_name=sample_text.txt  channels=${sg_user_channels}
    Run Keyword And Expect Error  ${expected_error}  Add Doc
    ...  url=${sg_url}  db=${sg_db}  doc=${doc_with_att}  auth=${sg_user_session}

    ${server_att_docs} =  Get Server Docs With Prefix  url=${cbs_url}  bucket=${bucket}  prefix=_sync:att:
    ${num_att_docs} =  Get Length  ${server_att_docs}
    Should Be Equal As Integers  ${num_att_docs}  ${0}


*** Keywords ***
Setup Test

    Log  Using cluster %{CLUSTER_CONFIG}  console=True

    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/reject_all_cc.json
    Reset Cluster  ${sg_config}

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}

    Set Test Variable  ${cbs_url}       ${cluster_hosts["couchbase_servers"][0]}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}

    Set Test Variable  ${sg_db}  db
    Set Test Variable  ${bucket}  data-bucket

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed  Fetch And Analyze Logs  ${TEST_NAME}

