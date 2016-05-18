*** Settings ***
Resource          resources/common.robot

Library     DebugLibrary

Library     ${Libraries}/NetworkUtils.py
Library     ${Libraries}/LoggingKeywords.py
Library     ${Keywords}/CouchbaseServer.py
Library     ${Keywords}/SyncGateway.py
Library     ${Keywords}/MobileRestClient.py
Library     ${Keywords}/Document.py

Test Setup      Setup Test
Test Teardown   Teardown Test


*** Test Cases ***
Test Attachment Revpos When Ancestor Unavailable
    [Documentation]    Creates a document with an attachment, then updates that document so that
    ...              the body of the revision that originally pushed the document is no
    ...              longer available.  Add a new revision that's not a child of the
    ...              active revision, and validate that it's uploaded successfully.
    ...              Example:
    ...                 1. Document is created with attachment at rev-1
    ...                 2. Document is updated (strip digests and length, only put revpos & stub) multiple times on the server, goes to rev-4
    ...                 3. Client attempts to add a new (conflicting) revision 2, with parent rev-1.
    ...                 4. If the body of rev-1 is no longer available on the server (temporary backup of revision has expired, and is no longer stored
    ...                   in the in-memory rev cache), we were throwing an error to client
    ...                   because we couldn't verify based on the _attachments property in rev-1.
    ...                 5. In this scenario, before returning error, we are now checking if the active revision has a common ancestor with the incoming revision.
    ...                  If so, we can validate any revpos values equal to or earlier than the common ancestor against the active revision.
    [Tags]           sanity    attachments  syncgateway

    Set Test Variable  ${cbs_url}       ${cluster_hosts["couchbase_servers"][0]}
    Set Test Variable  ${sg_url}        ${cluster_hosts["sync_gateways"][0]["public"]}
    Set Test Variable  ${sg_url_admin}  ${cluster_hosts["sync_gateways"][0]["admin"]}
    Set Test Variable  ${sg_db}  db
    Set Test Variable  ${bucket}  data-bucket

    ${sg_db} =  Set Variable  db

    ${channels_list} =  Create List  NBC
    ${user1} =  Create User  url=${sg_url_admin}  db=${sg_db}  name=user_1  password=password  channels=${channels_list}
    ${doc_with_att} =  Create Doc  id=att_doc  content={"sample_key": "sample_val"}  attachment=sample_text.txt  channels=${channels_list}

    ${doc_gen_1} =  Add Doc  url=${sg_url}  db=${sg_db}  doc=${doc_with_att}  auth=${user1}
    ${doc_gen_11} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_gen_1["id"]}  number_updates=${10}  auth=${user1}

    # Clear cached rev doc bodys from server and cycle sync_gateway
    Shutdown Sync Gateway  url=${sg_url}
    Delete Couchbase Server Cached Rev Bodies  url=${cbs_url}  bucket=${bucket}
    Start Sync Gateway  url=${sg_url}  config=${sg_config}

    ${conflict_doc} =  Add Conflict  url=${sg_url}  db=${sg_db}
    ...  doc_id=${doc_gen_1["id"]}
    ...  parent_revision=${doc_gen_1["rev"]}
    ...  new_revision=2-foo
    ...  auth=${user1}

*** Keywords ***
Setup Test
    Log  Using cluster %{CLUSTER_CONFIG}  console=True

    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json
    Reset Cluster  ${sg_config}

    ${cluster_hosts} =  Get Cluster Topology  %{CLUSTER_CONFIG}
    Set Test Variable  ${cluster_hosts}

Teardown Test
    Log  Tearing down test ...  console=True
    List Connections
    Run Keyword If Test Failed      Fetch And Analyze Logs

