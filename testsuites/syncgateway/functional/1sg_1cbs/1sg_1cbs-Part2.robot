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

    ${channels_list} =  Create List  NBC
    ${user1} =  Create User  url=${sg_url_admin}  db=${sg_db}  name=user_1  password=password  channels=${channels_list}
    ${doc_with_att} =  Create Doc  id=att_doc  content={"sample_key": "sample_val"}  attachment_name=sample_text.txt  channels=${channels_list}

    ${doc_gen_1} =  Add Doc  url=${sg_url}  db=${sg_db}  doc=${doc_with_att}  auth=${user1}
    ${doc_gen_11} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_gen_1["id"]}  number_updates=${10}  auth=${user1}

    # Clear cached rev doc bodys from server and cycle sync_gateway
    Stop Sync Gateway  url=${sg_url}
    Delete Couchbase Server Cached Rev Bodies  url=${cbs_url}  bucket=${bucket}
    Start Sync Gateway  url=${sg_url}  config=${sg_config}

    ${conflict_doc} =  Add Conflict  url=${sg_url}  db=${sg_db}
    ...  doc_id=${doc_gen_1["id"]}
    ...  parent_revisions=${doc_gen_1["rev"]}
    ...  new_revision=2-foo
    ...  auth=${user1}


Test Attachment Revpos When Ancestor Unavailable, Active Revision doesn't share ancestor
    [Documentation]    Creates a document with an attachment, then updates that document so that
    ...              the body of the revision that originally pushed the document is no
    ...              longer available.  Add a new revision that's not a child of the
    ...              active revision, and validate that it's uploaded successfully.
    ...              Example:
    ...                 1. Document is created with no attachment at rev-1
    ...                 2. Server adds revision with attachment at rev-2 {"hello.txt", revpos=2}
    ...                 2. Document is updated multiple times on the server, goes to rev-4
    ...                 3. Client attempts to add a new (conflicting) revision 3a, with ancestors rev-2a (with it's own attachment), rev-1.
    ...                 4. When client attempts to push rev-3a with attachment stub {"hello.txt", revpos=2}.  Should throw an error, since the revpos
    ...                 of the attachment is later than the common ancestor (rev-1)
    [Tags]  sanity  attachments  syncgateway

    Set Test Variable  ${sg_user_name}  sg_user
    Set Test Variable  ${sg_uset_password}  password

    ${sg_user_channels} =  Create List  NBC
    ${sg_user} =     Create User  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}  password=${sg_uset_password}  channels=${sg_user_channels}
    ${sg_user_session} =  Create Session  url=${sg_url_admin}  db=${sg_db}  name=${sg_user_name}

    ${doc} =  Create Doc  id=doc_1  content={"sample_key": "sample_val"}  channels=${sg_user_channels}
    ${doc_gen_1} =  Add Doc  url=${sg_url}  db=${sg_db}  doc=${doc}  auth=${sg_user_session}
    ${doc_gen_2} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_gen_1["id"]}  attachment_name=sample_text.txt  auth=${sg_user_session}
    ${doc_gen_3} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_gen_1["id"]}  auth=${sg_user_session}
    ${doc_gen_4} =  Update Doc  url=${sg_url}  db=${sg_db}  doc_id=${doc_gen_1["id"]}  auth=${sg_user_session}

    ${parent_rev_list} =  Create List  2-foo2  ${doc_gen_1["rev"]}

    # Sync Gateway should error since it has no references attachment in its ancestors
    Set Test Variable  ${expected_error}  HTTPError: 400 Client Error: Bad Request for url: */db/doc_1?new_edits=false
    Run Keyword And Expect Error  ${expected_error}  Add Conflict
    ...  url=${sg_url}
    ...  db=${sg_db}
    ...  doc_id=${doc_gen_1["id"]}
    ...  parent_revisions=${parent_rev_list}
    ...  new_revision=3-foo3
    ...  auth=${sg_user_session}

*** Keywords ***
Setup Test
    Log  Using cluster %{CLUSTER_CONFIG}  console=True

    Set Test Variable  ${sg_config}  ${SYNC_GATEWAY_CONFIGS}/sync_gateway_default_cc.json
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

